# Requirements Analysis

## What this exercise actually is
A self-paced, non-graded capability exercise (3-week window) assessing how
AI tools are used across the data engineering lifecycle, not just whether
the final pipeline runs. Effort weighting makes this explicit:

| Part | Focus | Weight |
|---|---|---|
| A | AI Workflow Foundation | 20% |
| B | Medallion Pipeline (Core + optional Stretch) | 60% |
| C | Submission & Reflection | 20% |

**Key implication:** the Core pipeline is scoped for only ~20-25 hours out
of the total effort. The remaining time is meant for the lifecycle
artifacts (requirement analysis, design notes, prompt history, testing/
debugging notes, reflection) — the brief explicitly warns against
expanding pipeline complexity at the expense of these. This directly
shaped our task order: artifacts and specs are written before any code
generation, not after.

## Non-negotiable requirements (Common Technical Requirements checklist)
These must all exist regardless of which stretch tier (if any) is chosen:
- Sample data generator with intentional quality issues
- Bronze ingestion (Python/PySpark)
- Silver validation — all 4 quality checks working
- Gold aggregation — all 3 aggregations (brief's checkbox list says "all 4"
  in one place but only 3 are specified in Section 7 — see Ambiguities below)
- Dashboard — 3+ SQL queries
- Database schema/setup script
- Seed/sample CSVs (customers, orders, products)
- Input validation and error handling
- Data quality reporting
- At least one meaningful test tier
- README setup instructions
- **Full prompt history** — flagged CRITICAL in the brief
- All planning/design/testing/debugging/reflection artifacts in-repo

## Exact data contract (fixed, not open to interpretation)
- `customers.csv`: 10,000 rows, 7 columns, PK `customer_id`
- `orders.csv`: 100,000 rows, 9 columns, PK `order_id`, FKs to customers
  and products
- `products.csv`: 500 rows, 7 columns, PK `product_id`
- Intentional issues total ~700 rows (~0.7% of orders) — exact counts
  captured in `project-context.md` and treated as ground truth for
  validating Silver's checks later.

## Where there's real design freedom
- **Type-validation / business-logic check (Silver check #5-equivalent):**
  the brief names exactly 3 check categories (completeness, uniqueness,
  referential integrity) but says "implement below quality checks" without
  a 4th named category, while the repo structure implies 5 check scripts.
  Resolved in `design-notes.md`.
- **Which rows feed Gold:** default assumed to be Silver-passed rows only,
  per our `spec.md`, since Gold is described as reading from Silver's
  validated data — but the brief doesn't explicitly forbid including
  flagged rows with a caveat. Documented as an assumption, not silently
  decided.
- **S3 vs DBFS:** brief says "S3/DBFS" — resolved to DBFS (see
  `design-notes.md`) purely for setup simplicity, no AWS account needed.
- **Stretch tier:** not yet decided whether to attempt one — Core alone
  already covers 100% of the required artifact checklist.

## Ambiguity worth flagging explicitly (not silently resolved)
The Core Acceptance Criteria checklist item says "Gold layer creates all 4
aggregations," but Section 7.4 only defines 3 aggregations (Sales by
Product, Revenue by Customer, Customer Segmentation) plus a separate
"daily/weekly trends" script that's positioned as supporting the dashboard
rather than a 4th standalone aggregation. Our `spec.md` treats
`03_daily_weekly_trends.sql` as the 4th Gold artifact to satisfy the
literal "4" count, while keeping the three named business aggregations as
the primary ones. This is called out here rather than picked silently, in
case it needs revisiting once the checklist's full text is available.

## What this means for task sequencing
Because Gold depends on Silver's actual output schema (the
`quality_check_result` column and which rows pass), and Silver depends on
Bronze's actual ingested schema, code generation order is fixed:
data generation → Bronze → Silver → Gold → Dashboard. This is reflected as
strict dependencies in `task-breakdown.md`.
