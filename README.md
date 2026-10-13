# clone-web

A single-file Python CLI tool, optimized for **Termux** and local
environments, that archives a webpage's HTML, CSS, and images into a local
folder and serves it offline through a local Flask server.

## Features

- Stylish colored terminal menu header
- `[1] Offline Directory Archive & Local Server` workflow:
  1. Prompts for a 4-digit local port (e.g. `5000`, `8080`)
  2. Prompts for a target website URL
  3. Shows a spinning-wheel loading animation while working
  4. Downloads the page's HTML, linked CSS files, and `<img>` images into
     a timestamped local folder, then rewrites the HTML tags to point at
     the local copies
  5. Starts a Flask server bound to `127.0.0.1` on your chosen port
  6. Prints the local URL (e.g. `http://127.0.0.1:8080`) so you can open
     it in your browser

## Requirements

Install these pip packages before running the tool:

## GIT clone 
```bash
git clone https://github.com/UG-ALOK/clone-web.git
```
## DIRECTORY OPEN
```bash
cd clone-web
```
## INSTALLATION REQUIREMENT PACKAGE
```bash
bash install.sh
```

## Usage
## RUN TOOL 
```bash
python3 voidsnapshot.py
```

Then follow the on-screen menu:

```
[1] Offline Directory Archive & Local Server
[0] Exit
```

Archived sites are saved under `./vm_archives/<domain>_<timestamp>/`.

## Known Limitations

- Only same-page `<link rel="stylesheet">` and `<img>` assets are
  downloaded (CSS files that themselves reference other assets like
  `@import` or `url()` background images are not recursively followed).
- JavaScript-driven or dynamically-loaded content will not be captured,
  since only the initial HTML response is parsed.
- Intended for archiving a single page at a time, not a full multi-page
  crawl.

## Legal / Ethical Use
🙏
Please read **DISCLAIMER.md** before using this tool. Only archive sites
you own or have explicit permission to copy, and always respect
copyright law, each site's Terms of Service, and `robots.txt`.
