from datetime import date, datetime
import json
from playwright.sync_api import sync_playwright
from typing import List

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

class Invoice(BaseModel):
    number: int
    issue_date: date
    amount: str


def test_download_invoices():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        page.goto("https://mywheels.nl/mijn/financien", timeout=10000)
        print("")

        invoices: List[Invoice] = []
        table_selector = "div.mb-12:nth-child(2) > div:nth-child(1) > div:nth-child(2) > table:nth-child(1) > tbody:nth-child(2)"
        page.wait_for_selector(table_selector, timeout=5000)
        for row in page.locator(f"{table_selector} > tr").all():
            for col in row.locator("td").all():
                values = col.all_inner_texts()[0].split("\n")
                if len(values) == 2:
                    if values[0] == "#":
                        number = int(values[1])
                    elif values[0] == "Factuurdatum":
                        issue_date = datetime.strptime(values[1], "%d-%m-%Y").date()
                    elif values[0] == "Totaalbedrag":
                        amount = values[1]
            invoices.append(
                Invoice(
                    number=number,
                    issue_date=issue_date,
                    amount=amount
                )
            )

        with open("invoices.json", "w") as f:
            f.write(json.dumps(invoices, indent=2, default=to_jsonable_python))

        browser.close()