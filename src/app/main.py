import argparse
from contextlib import closing, contextmanager
from datetime import date, datetime
import json
import sqlite3
from time import sleep
from typing import Generator
from playwright.sync_api import sync_playwright, Page
from pydantic import BaseModel
from pydantic_core import to_jsonable_python


class Invoice(BaseModel):
    number: int
    issue_date: date
    currency: str
    amount_cents: int


def _invoice_row_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return Invoice(**{k: v for k, v in zip(fields, row)})


@contextmanager
def _prepare_db():
    with closing(sqlite3.connect("mywheels.db")) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS invoices (number INTEGER PRIMARY KEY, issue_date TEXT, currency TEXT, amount_cents INTEGER)"
        )
        conn.total_changes
        yield conn


def _find_invoices_in(page: Page) -> list[Invoice]:
    table_selector = "div.mb-12:nth-child(2) > div:nth-child(1) > div:nth-child(2) > table:nth-child(1) > tbody:nth-child(2)"
    page.wait_for_selector(table_selector, timeout=5000)

    invoices: list[Invoice] = []
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
                        parts = values[1].split(" ")
                        if len(parts) == 2:
                            currency = parts[0]
                            amount_cents = int(float(parts[1].replace(",", ".")) * 100)
                        elif len(parts) == 3:
                            currency = parts[1]
                            amount_cents = (
                                int(float(parts[2].replace(",", ".")) * 100) * -1
                            )
                        else:
                            raise ValueError(f"don't know how to handle this: {parts}")
        invoices.append(
            Invoice(
                number=number,
                issue_date=issue_date,
                currency=currency,
                amount_cents=amount_cents,
            )
        )
    return invoices


def _download_invoices(conn):
    cursor = conn.cursor()
    last_invoice = cursor.execute("SELECT MAX(number) FROM invoices").fetchone()
    last_invoice_number = None
    if last_invoice is not None:
        last_invoice_number = last_invoice[0]

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        page.set_default_timeout(10000)
        page.goto("https://mywheels.nl/mijn/financien", timeout=10000)

        list_selector = "div.mb-12:nth-child(2) > div:nth-child(1) > ul:nth-child(3)"
        page.wait_for_selector(list_selector, timeout=5000)
        list_locator = page.locator(list_selector)
        list_item_locator = list_locator.locator("li")

        next = 1
        last = int(list_item_locator.last.text_content())
        print(f"{last} pages to download")

        invoices: list[Invoice] = _find_invoices_in(page)
        for i in invoices:
            if last_invoice_number is not None and i.number == last_invoice_number:
                print(f"invoices prior to #{last_invoice_number} (included) have already been stored. skipping.")
                return

            cursor.execute(
                "INSERT INTO invoices (number, issue_date, currency, amount_cents) VALUES (?, ?, ?, ?)",
                [
                    i.number,
                    i.issue_date.strftime("%Y-%m-%d"),
                    i.currency,
                    i.amount_cents,
                ],
            )
        print(f"downloaded invoices for page 1")

        while next < last:
            page.wait_for_selector(list_selector, timeout=5000)
            next = int(list_item_locator.locator(".bg-blue").text_content()) + 1
            list_item_locator.get_by_text(str(next), exact=True).click()
            sleep(1)
            invoices = _find_invoices_in(page)

            for i in invoices:
                cursor.execute(
                    "INSERT INTO invoices (number, issue_date, currency, amount_cents) VALUES (?, ?, ?, ?)",
                    [
                        i.number,
                        i.issue_date.strftime("%Y-%m-%d"),
                        i.currency,
                        i.amount_cents,
                    ],
                )
            print(f"downloaded invoices for page {next}")

        conn.commit()
        browser.close()


def _to_csv(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.row_factory = _invoice_row_factory
    invoices = cursor.execute(
        "SELECT number, issue_date, currency, amount_cents FROM invoices ORDER BY number"
    ).fetchall()
    with open("invoices.csv", "w") as f:
        f.write("number,date,currency,amount_cents\n")
        for invoice in invoices:
            f.write(
                f"{invoice.number},{invoice.issue_date.strftime("%Y-%m-%d")},{invoice.currency},{invoice.amount_cents}\n"
            )


def _to_json(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.row_factory = _invoice_row_factory
    invoices = cursor.execute(
        "SELECT number, issue_date, currency, amount_cents FROM invoices ORDER BY number"
    ).fetchall()
    with open("invoices.json", "w") as f:
        f.write(json.dumps(invoices, indent=2, default=to_jsonable_python))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="mywheels-scraper",
        description="Collects invoice history from MyWheels",
    )
    parser.add_argument("--download", type=bool)
    parser.add_argument("--export", type=str, nargs="*", choices=["csv", "json"])
    args = parser.parse_args()
    if args.export:
        args.export = set(args.export)

    with _prepare_db() as conn:
        if args.download:
            _download_invoices(conn)
        if args.export:
            if "csv" in args.export:
                _to_csv(conn)
            if "json" in args.export:
                _to_json(conn)
