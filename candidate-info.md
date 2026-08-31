# Candidate Information

**Name:** Sanjeev Yadav
**Role:** SSE
**Primary Technology Stack:** Python / PySpark, SQL, Databricks
**Primary AI Tool Used:** Cursor / Claude
**Project Option Selected:** Data Pipeline (Medallion Architecture)
**Assessment Start Date:** 29-08-2026
**Submission Date:** 31-08-2026

## Tools & Environment

- Databricks: Free Edition (Serverless SQL Warehouse + Serverless Compute)
- Languages: Python, PySpark, SQL
- Libraries: PySpark, Delta Lake
- AI Tool: Cursor (code generation) / Claude (design, specs, documentation)

## Setup Summary

Full setup instructions are in README.md and database/setup-notes.md. Quick reference:
1. Generate seed data: `python src/data_generation/generate_sample_data.py`
2. Upload CSVs to the Unity Catalog Volume `/Volumes/workspace/default/raw_data/`
3. Run Bronze → Silver → Gold pipeline scripts in order
4. Build the Databricks SQL Dashboard (see src/dashboard/DASHBOARD_GUIDE.md)
5. Verify with tests/run_all_tests.py
