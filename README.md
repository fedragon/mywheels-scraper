# Mywheels scraper

aka: what you end up doing when you periodically want to know how much you're spending using the [MyWheels](https://mywheels.nl) service, but there's "download all invoices to CSV" button on their website.

This small utility collects my invoices' history from the [MyWheels website](https://mywheels.nl), storing them to a local sqlite3 database and (optionally) exporting them to CSV and/or JSON. When run over an existing database, it only collects the new invoices, if any.

## Run

1. Run the Chromium version installed by Playwright in debug mode, e.g.

```
~/Library/Caches/ms-playwright/chromium-1140/chrome-mac/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=9222
```

2. In the browser window that just opened, login to your MyWheels account

3. Run

```
uv run src/app/main.py --download 1 -- export csv json
```
