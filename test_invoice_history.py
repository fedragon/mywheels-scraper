from datetime import date, datetime
import json
from time import sleep
from playwright.sync_api import sync_playwright
from typing import List

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

class Invoice(BaseModel):
    number: int
    issue_date: date
    amount: str


def get_invoices(page) -> list[Invoice]:
    table_selector = "div.mb-12:nth-child(2) > div:nth-child(1) > div:nth-child(2) > table:nth-child(1) > tbody:nth-child(2)"
    page.wait_for_selector(table_selector, timeout=5000)

    invoices: List[Invoice] = []
    for row in page.locator(f"{table_selector} > tr").all():
        for col in row.locator("td").all():
            for text in col.all_inner_texts():
                values = text.split("\n")
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
                amount=amount.replace(",", ".")
            )
        )
    return invoices


def test_download_invoices():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        page.set_default_timeout(10000)
        page.goto("https://mywheels.nl/mijn/financien", timeout=10000)
        print("")

        list_selector = "div.mb-12:nth-child(2) > div:nth-child(1) > ul:nth-child(3)"
        page.wait_for_selector(list_selector, timeout=5000)
        list_locator = page.locator(list_selector)
        list_item_locator = list_locator.locator("li")

        next = 1
        last = int(list_item_locator.last.text_content())
        print("last", last)

        all_invoices: list[Invoice] = get_invoices(page)
        print(f"downloaded invoices for page 1")

        while next < last:
            page.wait_for_selector(list_selector, timeout=5000)
            next = int(list_item_locator.locator(".bg-blue").text_content()) + 1

            list_item_locator.get_by_text(str(next), exact=True).click()
            sleep(1)
            all_invoices = all_invoices + get_invoices(page)
            print(f"downloaded invoices for page {next}")

        with open("invoices.json", "w") as f:
            f.write(json.dumps(all_invoices, indent=2, default=to_jsonable_python))

        with open("invoices.csv", "w") as f:
            f.write("number,date,amount\n")
            for invoice in all_invoices:
                f.write(f"{invoice.number},{invoice.issue_date.strftime("%Y-%m-%d")},{invoice.amount.strip("€ ")}\n")

        browser.close()