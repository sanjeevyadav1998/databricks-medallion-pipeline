"""
Generate realistic e-commerce sample CSVs with intentional data quality issues.

Runs before the Bronze layer; output feeds raw ingestion. Uses a fixed seed so
every run produces identical files for reproducible Silver-layer testing.
"""

from __future__ import annotations

import csv
import random
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Neither pandas nor Faker is installed in this environment; pure stdlib is used.
# If both become available, swap to pandas DataFrame writes + Faker for names/emails.
USE_PANDAS = False
USE_FAKER = False

try:
    import pandas as pd  # noqa: F401

    USE_PANDAS = True
except ImportError:
    pass

try:
    from faker import Faker  # noqa: F401

    USE_FAKER = True
except ImportError:
    pass

RANDOM_SEED = 42

# Paths relative to this script — no hardcoded absolute paths.
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent.parent / "data"

CUSTOMERS_PATH = OUTPUT_DIR / "customers.csv"
ORDERS_PATH = OUTPUT_DIR / "orders.csv"
PRODUCTS_PATH = OUTPUT_DIR / "products.csv"

CUSTOMER_ROW_COUNT = 10_000
ORDER_ROW_COUNT = 100_000
PRODUCT_ROW_COUNT = 500

# Issue counts (exact targets from project spec).
NULL_EMAIL_COUNT = 50
DUPLICATE_CUSTOMER_ID_COUNT = 10
NULL_CUSTOMER_ID_COUNT = 100
NULL_PRODUCT_ID_COUNT = 200
ORPHAN_CUSTOMER_ID_COUNT = 50
ORPHAN_PRODUCT_ID_COUNT = 30
DUPLICATE_ORDER_ID_COUNT = 20

# ASSUMPTION: representative e-commerce countries weighted toward larger markets.
COUNTRIES = [
    "United States",
    "United Kingdom",
    "Germany",
    "France",
    "Canada",
    "Australia",
    "India",
    "Netherlands",
    "Spain",
    "Italy",
]

CUSTOMER_SEGMENTS = ["Premium", "Standard", "Basic"]

# ASSUMPTION: broad retail categories aligned with a general e-commerce catalog.
PRODUCT_CATEGORIES = [
    "Electronics",
    "Clothing",
    "Home & Garden",
    "Sports & Outdoors",
    "Books",
    "Beauty",
    "Toys",
    "Groceries",
]

ORDER_STATUSES = ["Pending", "Completed", "Cancelled"]

FIRST_NAMES = [
    "James",
    "Maria",
    "Chen",
    "Aisha",
    "Liam",
    "Sofia",
    "Noah",
    "Emma",
    "Olivia",
    "Ethan",
    "Priya",
    "Lucas",
    "Isabella",
    "Arjun",
    "Mia",
]

LAST_NAMES = [
    "Smith",
    "Patel",
    "Garcia",
    "Kim",
    "Mueller",
    "Nguyen",
    "Brown",
    "Singh",
    "Taylor",
    "Rossi",
    "Lee",
    "Martin",
    "Khan",
    "Wilson",
    "Dubois",
]

PRODUCT_ADJECTIVES = ["Pro", "Essential", "Ultra", "Classic", "Smart", "Eco", "Deluxe"]
PRODUCT_NOUNS = [
    "Headphones",
    "Jacket",
    "Blender",
    "Yoga Mat",
    "Novel",
    "Moisturizer",
    "Drone",
    "Sneakers",
    "Lamp",
    "Backpack",
]

CUSTOMER_COLUMNS = [
    "customer_id",
    "customer_name",
    "email",
    "country",
    "signup_date",
    "customer_segment",
    "lifetime_value",
]

ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "product_id",
    "quantity",
    "unit_price",
    "total_amount",
    "order_status",
    "payment_date",
]

PRODUCT_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "price",
    "cost",
    "stock_quantity",
    "reorder_level",
]


def _money(value: float | Decimal) -> str:
    """Format monetary values consistently for CSV output."""
    quantized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _random_date(rng: random.Random, start: date, end: date) -> date:
    """Return a uniform random date in the inclusive [start, end] range."""
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))


def _customer_name(rng: random.Random) -> str:
    """Build a plausible customer display name."""
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _email_for_name(rng: random.Random, name: str, customer_id: int) -> str:
    """Derive a deterministic-ish email from name and id for realistic variety."""
    local_part = name.lower().replace(" ", ".")
    domain = rng.choice(["mail.example.com", "shopmail.io", "customer.co", "inbox.net"])
    return f"{local_part}.{customer_id}@{domain}"


def _product_name(rng: random.Random, product_id: int) -> str:
    """Build a short product label."""
    return f"{rng.choice(PRODUCT_ADJECTIVES)} {rng.choice(PRODUCT_NOUNS)} {product_id}"


def generate_products(rng: random.Random) -> list[dict[str, str]]:
    """
    Create the product catalog (500 rows, clean PKs).

    Cost is always below price; stock and reorder levels reflect typical inventory.
    """
    rows: list[dict[str, str]] = []
    for product_id in range(1, PRODUCT_ROW_COUNT + 1):
        category = rng.choice(PRODUCT_CATEGORIES)
        # ASSUMPTION: retail price band 9.99–499.99 for this exercise catalog.
        price = rng.uniform(9.99, 499.99)
        margin = rng.uniform(0.15, 0.55)
        cost = price * (1 - margin)
        stock_quantity = rng.randint(0, 2_000)
        reorder_level = rng.randint(10, 200)

        rows.append(
            {
                "product_id": str(product_id),
                "product_name": _product_name(rng, product_id),
                "category": category,
                "price": _money(price),
                "cost": _money(cost),
                "stock_quantity": str(stock_quantity),
                "reorder_level": str(reorder_level),
            }
        )
    return rows


def generate_customers(rng: random.Random) -> list[dict[str, str]]:
    """
    Create 10,000 customer rows with exact NULL-email and duplicate-PK injections.

    Duplicate rows reuse customer_id 1..10 on the last 10 rows so each issue type
    stays on distinct rows where possible.
    """
    rows: list[dict[str, str]] = []
    signup_start = date(2018, 1, 1)
    signup_end = date(2025, 8, 31)

    for customer_id in range(1, CUSTOMER_ROW_COUNT + 1):
        name = _customer_name(rng)
        segment = rng.choices(
            CUSTOMER_SEGMENTS,
            weights=[0.2, 0.5, 0.3],
            k=1,
        )[0]
        # ASSUMPTION: lifetime_value skews lower with occasional high-value customers.
        lifetime_value = rng.lognormvariate(5.5, 0.8)
        lifetime_value = min(max(lifetime_value, 0.0), 5_000.0)

        rows.append(
            {
                "customer_id": str(customer_id),
                "customer_name": name,
                "email": _email_for_name(rng, name, customer_id),
                "country": rng.choice(COUNTRIES),
                "signup_date": _random_date(rng, signup_start, signup_end).isoformat(),
                "customer_segment": segment,
                "lifetime_value": _money(lifetime_value),
            }
        )

    # NULL emails on 50 clean-PK rows (avoid duplicate-row indices and ids 1..10).
    null_email_indices = list(range(200, 200 + NULL_EMAIL_COUNT))
    for idx in null_email_indices:
        rows[idx]["email"] = ""

    # Duplicate customer_id: last 10 rows reuse ids 1..10 (already present above).
    duplicate_indices = list(range(CUSTOMER_ROW_COUNT - DUPLICATE_CUSTOMER_ID_COUNT, CUSTOMER_ROW_COUNT))
    for offset, idx in enumerate(duplicate_indices):
        reused_id = offset + 1
        source = rows[reused_id - 1]
        rows[idx]["customer_id"] = str(reused_id)
        rows[idx]["customer_name"] = source["customer_name"]
        rows[idx]["email"] = source["email"]
        rows[idx]["country"] = source["country"]
        rows[idx]["signup_date"] = source["signup_date"]
        rows[idx]["customer_segment"] = source["customer_segment"]
        rows[idx]["lifetime_value"] = source["lifetime_value"]

    return rows


def _payment_date_for_status(
    rng: random.Random,
    order_date: date,
    order_status: str,
) -> str:
    """
    Apply payment_date business rules from the spec.

    Pending orders have no payment; Completed always do; Cancelled may or may not.
    """
    if order_status == "Pending":
        return ""
    if order_status == "Completed":
        lag = rng.randint(0, 7)
        return (order_date + timedelta(days=lag)).isoformat()
    # Cancelled — ~40% retain a payment attempt date before cancellation.
    if rng.random() < 0.4:
        lag = rng.randint(0, 3)
        return (order_date + timedelta(days=lag)).isoformat()
    return ""


def _base_order_row(
    rng: random.Random,
    order_id: int,
    product_price_lookup: dict[int, Decimal],
    valid_customer_ids: list[int],
) -> dict[str, str]:
    """Build one order row with valid FKs and consistent total_amount."""
    customer_id = rng.choice(valid_customer_ids)
    product_id = rng.randint(1, PRODUCT_ROW_COUNT)
    quantity = rng.randint(1, 10)
    unit_price = product_price_lookup[product_id]
    total_amount = unit_price * quantity

    order_start = date(2023, 1, 1)
    order_end = date(2025, 8, 31)
    order_date = _random_date(rng, order_start, order_end)
    order_status = rng.choices(
        ORDER_STATUSES,
        weights=[0.1, 0.82, 0.08],
        k=1,
    )[0]
    payment_date = _payment_date_for_status(rng, order_date, order_status)

    return {
        "order_id": str(order_id),
        "customer_id": str(customer_id),
        "order_date": order_date.isoformat(),
        "product_id": str(product_id),
        "quantity": str(quantity),
        "unit_price": _money(unit_price),
        "total_amount": _money(total_amount),
        "order_status": order_status,
        "payment_date": payment_date,
    }


def generate_orders(
    rng: random.Random,
    products: list[dict[str, str]],
    customers: list[dict[str, str]],
) -> list[dict[str, str]]:
    """
    Create 100,000 order rows with disjoint issue slices for testability.

    Each issue category occupies its own index range so counts are independently
    verifiable and rows do not combine multiple injected defects.
    """
    product_price_lookup = {
        int(row["product_id"]): Decimal(row["price"]) for row in products
    }
    valid_customer_ids = sorted({int(row["customer_id"]) for row in customers})

    rows: list[dict[str, str]] = []
    for order_id in range(1, ORDER_ROW_COUNT + 1):
        rows.append(
            _base_order_row(rng, order_id, product_price_lookup, valid_customer_ids)
        )

    # Disjoint issue ranges (400 rows total).
    null_customer_id_indices = range(0, NULL_CUSTOMER_ID_COUNT)
    null_product_id_indices = range(
        NULL_CUSTOMER_ID_COUNT,
        NULL_CUSTOMER_ID_COUNT + NULL_PRODUCT_ID_COUNT,
    )
    orphan_customer_id_indices = range(
        NULL_CUSTOMER_ID_COUNT + NULL_PRODUCT_ID_COUNT,
        NULL_CUSTOMER_ID_COUNT + NULL_PRODUCT_ID_COUNT + ORPHAN_CUSTOMER_ID_COUNT,
    )
    orphan_product_id_indices = range(
        NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT,
        NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT
        + ORPHAN_PRODUCT_ID_COUNT,
    )
    duplicate_order_id_indices = range(
        NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT
        + ORPHAN_PRODUCT_ID_COUNT,
        NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT
        + ORPHAN_PRODUCT_ID_COUNT
        + DUPLICATE_ORDER_ID_COUNT,
    )

    for idx in null_customer_id_indices:
        rows[idx]["customer_id"] = ""

    for idx in null_product_id_indices:
        rows[idx]["product_id"] = ""

    # ASSUMPTION: orphan customer_ids start at 10001 (above generated PK range).
    for offset, idx in enumerate(orphan_customer_id_indices):
        rows[idx]["customer_id"] = str(10_001 + offset)

    # ASSUMPTION: orphan product_ids start at 501 (above generated PK range).
    for offset, idx in enumerate(orphan_product_id_indices):
        rows[idx]["product_id"] = str(501 + offset)

    for offset, idx in enumerate(duplicate_order_id_indices):
        rows[idx]["order_id"] = rows[offset]["order_id"]

    return rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    """Persist rows to CSV with a stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _is_null(value: str | None) -> bool:
    """Treat empty strings as NULL for CSV-backed verification."""
    return value is None or value.strip() == ""


def _duplicate_row_count(values: list[str]) -> int:
    """
    Count rows that reuse a value already seen earlier in the file.

    Matches the spec wording: rows that reuse an id appearing elsewhere.
    """
    seen: set[str] = set()
    duplicate_rows = 0
    for value in values:
        if value in seen:
            duplicate_rows += 1
        else:
            seen.add(value)
    return duplicate_rows


def summarize_customers(rows: list[dict[str, str]]) -> dict[str, int]:
    """Count injected customer issues for stdout verification."""
    customer_ids = [row["customer_id"] for row in rows]
    null_emails = sum(1 for row in rows if _is_null(row["email"]))
    duplicate_customer_ids = _duplicate_row_count(customer_ids)
    return {
        "total_rows": len(rows),
        "null_email_rows": null_emails,
        "duplicate_customer_id_rows": duplicate_customer_ids,
    }


def summarize_orders(
    rows: list[dict[str, str]],
    valid_customer_ids: set[str],
    valid_product_ids: set[str],
) -> dict[str, int]:
    """Count injected order issues for stdout verification."""
    order_ids = [row["order_id"] for row in rows]
    null_customer_id = sum(1 for row in rows if _is_null(row["customer_id"]))
    null_product_id = sum(1 for row in rows if _is_null(row["product_id"]))
    orphan_customer_id = sum(
        1
        for row in rows
        if not _is_null(row["customer_id"]) and row["customer_id"] not in valid_customer_ids
    )
    orphan_product_id = sum(
        1
        for row in rows
        if not _is_null(row["product_id"]) and row["product_id"] not in valid_product_ids
    )
    duplicate_order_ids = _duplicate_row_count(order_ids)
    return {
        "total_rows": len(rows),
        "null_customer_id_rows": null_customer_id,
        "null_product_id_rows": null_product_id,
        "orphan_customer_id_rows": orphan_customer_id,
        "orphan_product_id_rows": orphan_product_id,
        "duplicate_order_id_rows": duplicate_order_ids,
    }


def print_summary(
    products: list[dict[str, str]],
    customers: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> None:
    """Log row counts and verified issue counts after generation."""
    valid_customer_ids = {row["customer_id"] for row in customers}
    valid_product_ids = {row["product_id"] for row in products}
    customer_stats = summarize_customers(customers)
    order_stats = summarize_orders(orders, valid_customer_ids, valid_product_ids)

    print("Sample data generation complete.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Library choice: pandas={USE_PANDAS}, faker={USE_FAKER} (stdlib csv/random active)")
    print()
    print(f"products.csv — total rows: {len(products)}")
    print()
    print(f"customers.csv — total rows: {customer_stats['total_rows']}")
    print(f"  NULL email rows: {customer_stats['null_email_rows']}")
    print(f"  duplicate customer_id rows: {customer_stats['duplicate_customer_id_rows']}")
    print()
    print(f"orders.csv — total rows: {order_stats['total_rows']}")
    print(f"  NULL customer_id rows: {order_stats['null_customer_id_rows']}")
    print(f"  NULL product_id rows: {order_stats['null_product_id_rows']}")
    print(f"  orphan customer_id rows: {order_stats['orphan_customer_id_rows']}")
    print(f"  orphan product_id rows: {order_stats['orphan_product_id_rows']}")
    print(f"  duplicate order_id rows: {order_stats['duplicate_order_id_rows']}")


def main() -> None:
    """Generate all CSVs and print verification metrics."""
    rng = random.Random(RANDOM_SEED)

    products = generate_products(rng)
    customers = generate_customers(rng)
    orders = generate_orders(rng, products, customers)

    write_csv(PRODUCTS_PATH, PRODUCT_COLUMNS, products)
    write_csv(CUSTOMERS_PATH, CUSTOMER_COLUMNS, customers)
    write_csv(ORDERS_PATH, ORDER_COLUMNS, orders)

    print_summary(products, customers, orders)


if __name__ == "__main__":
    main()
