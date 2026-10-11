#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-----------
    python voidsnapshot.py

LEGAL / ETHICAL NOTE
----------------------
Only archive sites you own, or that you have explicit permission to copy.
Respect copyright law, each site's Terms of Service, and robots.txt.
This tool is intended for personal archiving, offline reading, testing,
and educational use only. See DISCLAIMER.md for full details.
================================================================================
"""

import os
import sys
import time
import hashlib
import itertools
import threading
import urllib.parse as urlparse
from datetime import datetime

# ------------------------------------------------------------------------
# Dependency checks — fail fast with a friendly, actionable message instead
# of a raw traceback if a required package is missing.
# ------------------------------------------------------------------------
try:
    import requests
except ImportError:
    print("[!] Missing dependency: 'requests'")
    print("    Install it with:  pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Missing dependency: 'beautifulsoup4'")
    print("    Install it with:  pip install beautifulsoup4")
    sys.exit(1)

try:
    from flask import Flask, send_from_directory
except ImportError:
    print("[!] Missing dependency: 'flask'")
    print("    Install it with:  pip install flask")
    sys.exit(1)


# ============================================================================
# COLOR CODES  (ANSI escape sequences — work in Termux, Linux, macOS, and
# most modern Windows terminals)
# ============================================================================
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


# A believable desktop User-Agent header. This is sent honestly to reduce
# the chance of being blocked by naive bot filters — it does not spoof
# identity beyond a standard browser string, and does not bypass logins,
# paywalls, CAPTCHAs, or any access controls.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

OUTPUT_ROOT = "vm_archives"  # where archived sites are stored, relative to CWD


# ============================================================================
# UI HELPERS
# ============================================================================
def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def print_banner():
    line = "=" * 62
    print(f"{C.CYAN}{C.BOLD}{line}{C.RESET}")
    print(f"{C.MAGENTA}{C.BOLD}      V O I D S N A P S H O T   U T I L I T Y{C.RESET}")
    print(f"{C.DIM}      Offline Site Archiver + Local Flask Server{C.RESET}")
    print(f"{C.DIM}      (Optimized for Termux & local environments){C.RESET}")
    print(f"{C.CYAN}{C.BOLD}{line}{C.RESET}")


def print_section(title):
    print(f"\n{C.BLUE}{C.BOLD}>>> {title}{C.RESET}\n")


# ============================================================================
# SPINNER — smooth spinning-wheel loading animation on a background thread
# ============================================================================
class Spinner:
    def __init__(self, message="Processing"):
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None

    def _spin(self):
        frames = itertools.cycle(["|", "/", "-", "\\"])
        while not self._stop_event.is_set():
            frame = next(frames)
            sys.stdout.write(f"\r{C.YELLOW}[{frame}] {self.message}...{C.RESET}")
            sys.stdout.flush()
            time.sleep(0.1)
        # clear the spinner line once stopped
        sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")
        sys.stdout.flush()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_message=None):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
        if final_message:
            print(final_message)


# ============================================================================
# INPUT VALIDATION
# ============================================================================
def prompt_port():
    """Ask the user for a 4-digit local port number, validating input."""
    while True:
        raw = input(
            f"{C.CYAN}[?] Enter a 4-digit port number for localhost "
            f"(e.g. 5000, 8080): {C.RESET}"
        ).strip()
        if raw.isdigit() and len(raw) == 4:
            port = int(raw)
            if 1024 <= port <= 9999:
                return port
        print(f"{C.RED}[!] Invalid port. Enter exactly 4 digits, 1024-9999.{C.RESET}")


def prompt_url():
    """Ask the user for a target URL, validating it has a scheme + host."""
    while True:
        raw = input(
            f"{C.CYAN}[?] Enter the target website URL "
            f"(include http:// or https://): {C.RESET}"
        ).strip()
        parsed = urlparse.urlparse(raw)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return raw
        print(f"{C.RED}[!] Invalid URL. Must start with http:// or https://{C.RESET}")


# ============================================================================
# SITE ARCHIVER — fetches the page, downloads CSS + images, rewrites HTML
# ============================================================================
class SiteArchiver:
    """
    Downloads a single webpage plus its linked stylesheets and images,
    saves everything into a timestamped local folder, and rewrites the
    HTML tags to point at the local copies so the page renders offline.
    """

    def __init__(self, url, output_root=OUTPUT_ROOT):
        self.url = url
        parsed = urlparse.urlparse(url)
        domain = parsed.netloc.replace(":", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder_name = f"{domain}_{timestamp}"
        self.output_dir = os.path.join(output_root, self.folder_name)
        self.assets_dir = os.path.join(self.output_dir, "assets")
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _make_dirs(self):
        os.makedirs(self.assets_dir, exist_ok=True)

    @staticmethod
    def _safe_filename(asset_url):
        """Build a filesystem-safe filename from an asset URL."""
        parsed = urlparse.urlparse(asset_url)
        name = os.path.basename(parsed.path)
        if not name:
            name = hashlib.md5(asset_url.encode("utf-8")).hexdigest()[:12]
        if "." not in name:
            name += ".asset"
        # strip characters that are awkward on some filesystems
        return "".join(ch for ch in name if ch not in '<>:"|?*')

    def _download_asset(self, asset_url):
        """Download a single CSS or image asset; return its new relative path."""
        try:
            full_url = urlparse.urljoin(self.url, asset_url)
            resp = self.session.get(full_url, timeout=10)
            resp.raise_for_status()

            filename = self._safe_filename(full_url)
            base, ext = os.path.splitext(filename)
            local_path = os.path.join(self.assets_dir, filename)

            # avoid overwriting files that share the same name
            counter = 1
            while os.path.exists(local_path):
                filename = f"{base}_{counter}{ext}"
                local_path = os.path.join(self.assets_dir, filename)
                counter += 1

            with open(local_path, "wb") as f:
                f.write(resp.content)

            return f"assets/{filename}"
        except requests.exceptions.RequestException as e:
            print(f"{C.YELLOW}[!] Skipped asset ({asset_url}): {e}{C.RESET}")
            return None
        except OSError as e:
            print(f"{C.YELLOW}[!] Could not save asset ({asset_url}): {e}{C.RESET}")
            return None

    def archive(self):
        """Fetch the page, download its assets, rewrite HTML, save to disk."""
        self._make_dirs()

        resp = self.session.get(self.url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # --- Stylesheets: <link rel="stylesheet" href="..."> ---
        for tag in soup.find_all("link", href=True):
            rel = tag.get("rel", [])
            rel_lower = [r.lower() for r in rel] if rel else []
            if "stylesheet" in rel_lower:
                new_path = self._download_asset(tag["href"])
                if new_path:
                    tag["href"] = new_path

        # --- Images: <img src="..."> ---
        for tag in soup.find_all("img", src=True):
            new_path = self._download_asset(tag["src"])
            if new_path:
                tag["src"] = new_path

        # --- Simplify <img srcset="..."> so the browser doesn't try to
        #     fetch remote responsive-image variants we didn't download ---
        for tag in soup.find_all("img", attrs={"srcset": True}):
            del tag["srcset"]

        # --- Background images referenced via inline style="background-image:url(...)" ---
        for tag in soup.find_all(style=True):
            style = tag["style"]
            if "url(" in style:
                pass

        index_path = os.path.join(self.output_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        return self.output_dir


# ============================================================================
# LOCAL FLASK SERVER
# ============================================================================
def start_local_server(directory, port):
    """Serve the archived directory at http://127.0.0.1:<port>/"""
    app = Flask(__name__)
    directory = os.path.abspath(directory)

    @app.route("/")
    def index():
        return send_from_directory(directory, "index.html")

    @app.route("/<path:filename>")
    def files(filename):
        return send_from_directory(directory, filename)

    print(f"{C.GREEN}{C.BOLD}[OK] Local server running at: "
          f"http://127.0.0.1:{port}{C.RESET}")
    print(f"{C.DIM}     Open that address in your browser to view the "
          f"offline snapshot.{C.RESET}")
    print(f"{C.DIM}     Press CTRL+C to stop the server.{C.RESET}\n")

    app.run(host="127.0.0.1", port=port, use_reloader=False)


# ============================================================================
# WORKFLOW: OPTION 1 — Offline Directory Archive & Local Server
# ============================================================================
def run_offline_archive():
    print_section("Offline Directory Archive & Local Server")

    port = prompt_port()
    url = prompt_url()

    spinner = Spinner("Fetching page and downloading assets")
    spinner.start()

    output_dir = None
    try:
        archiver = SiteArchiver(url)
        output_dir = archiver.archive()
        spinner.stop(
            f"{C.GREEN}[OK] Website archived successfully -> {output_dir}{C.RESET}"
        )
    except requests.exceptions.Timeout:
        spinner.stop(f"{C.RED}[!] Request timed out while fetching the site.{C.RESET}")
        return
    except requests.exceptions.ConnectionError:
        spinner.stop(f"{C.RED}[!] Could not connect. Check the URL and your network.{C.RESET}")
        return
    except requests.exceptions.HTTPError as e:
        spinner.stop(f"{C.RED}[!] Server returned an error: {e}{C.RESET}")
        return
    except requests.exceptions.RequestException as e:
        spinner.stop(f"{C.RED}[!] Network error while fetching site: {e}{C.RESET}")
        return
    except OSError as e:
        spinner.stop(f"{C.RED}[!] Filesystem error while saving files: {e}{C.RESET}")
        return
    except Exception as e:
        spinner.stop(f"{C.RED}[!] Unexpected error during archiving: {e}{C.RESET}")
        return

    if not output_dir:
        return

    try:
        start_local_server(output_dir, port)
    except OSError as e:
        print(f"{C.RED}[!] Could not start server on port {port}: {e}{C.RESET}")
        print(f"{C.DIM}    The port may already be in use - try a different one.{C.RESET}")
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[!] Server stopped by user.{C.RESET}")


# ============================================================================
# MAIN MENU
# ============================================================================
def main_menu():
    while True:
        clear_screen()
        print_banner()
        print(f"\n{C.WHITE}{C.BOLD} MAIN MENU{C.RESET}")
        print(f" {C.CYAN}[1]{C.RESET} Offline Directory Archive & Local Server")
        print(f" {C.CYAN}[0]{C.RESET} Exit")

        choice = input(f"\n{C.YELLOW}Select an option: {C.RESET}").strip()

        if choice == "1":
            run_offline_archive()
        elif choice == "0":
            print(f"{C.MAGENTA}Goodbye!{C.RESET}")
            sys.exit(0)
        else:
            print(f"{C.RED}[!] Invalid option, please try again.{C.RESET}")

        input(f"\n{C.DIM}Press ENTER to return to the menu...{C.RESET}")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{C.RED}[!] Interrupted by user. Exiting.{C.RESET}")
        sys.exit(0)
