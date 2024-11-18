# Mywheels scraper

Small utility to collect my invoices' history from the [MyWheels website](https://mywheels.nl) for further analysis. It stores them to a local sqlite3 database and can export them to CSV and JSON.

## Run

1. Run the Chromium version installed by Playwright in debug mode, e.g.

```
~/Library/Caches/ms-playwright/chromium-1140/chrome-mac/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=9222
```

2. In the browser, login to your MyWheels account

3. Run

```
uv run src/app/main.py --download 1 -- export csv json
```