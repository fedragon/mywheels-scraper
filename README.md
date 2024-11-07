# Mywheels scraper

Small utility to collect my invoices' history from the [MyWheels website](https://mywheels.nl).

## Run

1. Run the Chromium version installed by Playwright in debug mode, e.g.

```
~/Library/Caches/ms-playwright/chromium-1140/chrome-mac/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=9222
```

2. In the browser, login to your MyWheels account

3. Run

```
uv run -- pytest -s --headed --browser chromium test_invoice_history.py
```