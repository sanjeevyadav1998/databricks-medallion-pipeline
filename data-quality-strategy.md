# Data Quality Strategy

Silver-layer validation for this project. Implementation lives in
`src/silver/01_quality_completeness.py` through `05_quality_business_logic.py`,
orchestrated by `src/silver/create_silver_tables.py`.

## `quality_check_result` convention

Every Silver row gets a `quality_check_result` column:

- `'PASSED'` if all checks pass for that row.
- Otherwise, a pipe-delimited list of `FAIL_*` codes (e.g.
  `'FAIL_NULL_CUSTOMER_ID|FAIL_ORPHAN_CUSTOMER_ID'`).

Rows are **never dropped** — failures are flagged, not deleted.

## Implemented checks (5 modules)

| # | Module | What it checks | `FAIL_*` code(s) |
|---|---|---|---|
| 1 | `01_quality_completeness.py` | NULL values in critical fields: `email` (customers), `customer_id` and `product_id` (orders) | `FAIL_NULL_EMAIL`, `FAIL_NULL_CUSTOMER_ID`, `FAIL_NULL_PRODUCT_ID` |
| 2 | `02_quality_uniqueness.py` | Duplicate primary keys: `customer_id` (customers), `order_id` (orders), `product_id` (products). Only the 2nd and later occurrences are flagged, so injected duplicate counts match the spec exactly. | `FAIL_DUPLICATE_CUSTOMER_ID`, `FAIL_DUPLICATE_ORDER_ID`, `FAIL_DUPLICATE_PRODUCT_ID` |
| 3 | `03_quality_type_validation.py` | Email format (must contain `@`), date validity on `signup_date` and `order_date` | `FAIL_INVALID_EMAIL_FORMAT`, `FAIL_INVALID_DATE` |
| 4 | `04_quality_referential_integrity.py` | Foreign key existence: `customer_id` must exist in customers, `product_id` must exist in products. NULL FKs are **excluded** from orphan checks (completeness owns those). Joins use `.select(key).distinct()` on parent tables to prevent row explosion from duplicate parent keys. | `FAIL_ORPHAN_CUSTOMER_ID`, `FAIL_ORPHAN_PRODUCT_ID` |
| 5 | `05_quality_business_logic.py` | `total_amount ≈ quantity × unit_price` (within 0.01 margin), `quantity > 0`, `price >= cost` on products | `FAIL_CALCULATION_MISMATCH`, `FAIL_INVALID_QUANTITY`, `FAIL_PRICE_BELOW_COST` |

## Quality Metrics Report (verified results)

After running `create_silver_tables(spark)`, the printed Data Quality
Metrics Report showed:

| Table | Passed | Total | % Passed |
|---|---|---|---|
| `silver_customers` | 9,940 | 10,000 | 99.40% |
| `silver_orders` | 99,600 | 100,000 | 99.60% |
| `silver_products` | 500 | 500 | 100.00% |

All **7 injected-issue target counts** were caught exactly:

| Check | Caught | Expected |
|---|---|---|
| `FAIL_NULL_EMAIL` (customers) | 50 | 50 |
| `FAIL_DUPLICATE_CUSTOMER_ID` (customers) | 10 | 10 |
| `FAIL_NULL_CUSTOMER_ID` (orders) | 100 | 100 |
| `FAIL_NULL_PRODUCT_ID` (orders) | 200 | 200 |
| `FAIL_ORPHAN_CUSTOMER_ID` (orders) | 50 | 50 |
| `FAIL_ORPHAN_PRODUCT_ID` (orders) | 30 | 30 |
| `FAIL_DUPLICATE_ORDER_ID` (orders) | 20 | 20 |

These figures are formalized as assertions in
[tests/test_data_quality.py](tests/test_data_quality.py) — see that file
rather than re-deriving counts here.

## Sample data quality issues

The seed data generator injects a **verified total of 460 problematic rows**:

- **60 in customers** (50 NULL emails + 10 duplicate `customer_id`)
- **400 in orders** (100 NULL `customer_id` + 200 NULL `product_id` +
  50 orphan `customer_id` + 30 orphan `product_id` + 20 duplicate
  `order_id`)

No quality issues were intentionally injected into `products.csv`
(500/500 rows pass Silver).

> **Note:** The exercise brief's approximate "~700" total issue estimate
> differs from this project's measured count of **460**. The real,
> verified number (460) is what this pipeline actually detected and
> asserted against — use 460 when reporting results for this project.

For the business rationale behind each injected issue type, see
[src/data_generation/DATA_GENERATION_NOTES.md](src/data_generation/DATA_GENERATION_NOTES.md).
