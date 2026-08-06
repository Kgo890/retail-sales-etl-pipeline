# Retail Sales ETL Pipeline

An end-to-end ETL pipeline that takes raw e-commerce transaction data, cleans and transforms it in Python/pandas, loads it into a PostgreSQL warehouse, and surfaces it through an 8-page Power BI dashboard.

## Overview

This project processes ~500K transaction records from a UK-based online retailer (2010–2011) — sales, cancellations, adjustments, and non-sale transactions — into a dimensional PostgreSQL model with 46 analytical views across 8 business categories.

Along the way I ran into (and fixed) a few real bugs: a sign error in cancellation quantities, a product-affinity query that exploded to 1.5M rows before I filtered it down, and an ETL sequencing issue that was quietly inflating a duplicate-detection metric by almost 20x. Those are documented below, since finding and fixing that stuff is most of what the job actually is.

## Architecture

```
UCI ML Repo — Online Retail Dataset (id=352)
        ↓
Extract (src/extract/dataset.py)
   — fetches dataset via ucimlrepo, saves as data.csv + data_ids.csv
        ↓
Python/pandas transform (src/transform/transaction.py)
   — classify transaction types (sale, cancellation, adjustment, etc.)
   — dedupe exact rows, flag potential duplicates
   — split into fact tables by transaction type
        ↓
PostgreSQL star schema (src/load/load_data.py)
   — dim_product, dim_customer, dim_country, dim_date
   — fact_sales, fact_cancellations, fact_adjustment, fact_non_sale
   — data_quality_potential_duplicates
        ↓
46 SQL analytical views (postgresql/analytics/)
   — 8 business-category schemas: sales, product, customer, geographic,
     cancellation, adjustment, non_sales, data_quality
        ↓
Power BI dashboard (Import mode, connected to PostgreSQL)
   — 8 pages, one per schema
```
## Data Model

The pipeline loads into a PostgreSQL star schema in the `public` schema — 4 dimension tables and 4 fact tables, plus a standalone data quality audit table. The 46 analytical views (organized into 8 business-category schemas) are all built on top of these 9 tables.

### Dimension Tables

#### `dim_date`

![dim_date table structure](assets/screenshots/dim_date.png)

Standard date dimension, one row per calendar day present in the dataset. Carries `year`, `month`, `month_name`, `week`, `day`, `day_of_week`, and `day_name` alongside the `date_key` — precomputing these avoids repeating date-part extraction logic across dozens of analytical views.

#### `dim_product`

![dim_product table structure](assets/screenshots/dim_product.png)

Deliberately minimal — just `stock_code` and `description`. The source dataset doesn't include product category, price tier, or other product attributes, so there was nothing else to model here without fabricating data that wasn't in the source.

#### `dim_customer`

![dim_customer table structure](assets/screenshots/dim_customer.png)

Just `customer_id`. Like `dim_product`, this stays minimal because the source dataset has no customer demographic or account-level attributes — this table exists mainly to enforce referential integrity and give customer-level views a clean join target.

#### `dim_country`

![dim_country table structure](assets/screenshots/dim_country.png)

Maps `country_key` to `country` name. Small lookup table, but it's used across nearly every geographic view.

### Fact Tables

#### `fact_sales`

![fact_sales table structure](assets/screenshots/fact_sales.png)

The core sales table — every legitimate sale transaction, with `revenue` precomputed (`quantity × unit_price`) at load time rather than recalculated in every view. `row_hash` is an MD5 hash of the transaction's identifying fields, used as a conflict key on load so re-running the pipeline doesn't create duplicate rows.

#### `fact_cancellations`

![fact_cancellations table structure](assets/screenshots/fact_cancellations.png)

Same structure as `fact_sales`, holding order cancellations separately rather than as negative-quantity rows mixed into `fact_sales`. Keeping cancellations in their own table made it possible to calculate cancellation rates cleanly (cancelled orders vs. total orders) without cancellations skewing core sales revenue figures.

#### `fact_adjustment`

![fact_adjustment table structure](assets/screenshots/fact_adjustment.png)

Holds account and inventory adjustments — rows identified during transform as adjustments rather than genuine customer transactions (e.g. negative unit prices, or zero-price inventory corrections with no customer attached).

#### `fact_non_sale`

![fact_non_sale table structure](assets/screenshots/fact_non_sale.png)

Zero-value transactions and administrative/postage line items (e.g. shipping charges, gift wrap, bank charges) that aren't real product sales but still needed to be tracked. Includes a `transaction_type` column to distinguish the different non-sale categories within this one table.

### Standalone Table

#### `data_quality_potential_duplicates`

![data_quality_potential_duplicates table structure](assets/screenshots/data_quality_potential_duplicates.png)

Holds transaction rows flagged as potential duplicates — rows sharing the same `invoice_no`, `stock_code`, and `quantity` after exact-duplicate rows were already removed. Each row carries `duplicate_group_count`, which reflects how many rows share that same invoice/stock/quantity combination, so a real cluster can be told apart from a lone false positive.

This isn't a dimension or fact table in the traditional sense — it's a standalone data quality audit table, kept separate from `fact_sales` so duplicate detection doesn't interfere with core sales reporting, while still being queryable on its own.

## Pipeline Files

| File | What it does |
|---|---|
| `src/extract/dataset.py` | Fetches the Online Retail dataset from the UCI ML Repo via `ucimlrepo`, saves it as `data.csv` and `data_ids.csv` under `data/raw/`. |
| `src/transform/transaction.py` | Core transform logic. Classifies every row into Sale / Cancellation / Account Adjustment / Inventory Adjustment / Zero-Value Transaction using a multi-condition rule (price sign, quantity sign, invoice prefix, customer ID). Drops exact duplicate rows, flags potential duplicates, computes `revenue`, and splits everything into separate CSVs per fact table under `data/processed/`. |
| `src/load/database.py` | Sets up the SQLAlchemy engine connection to PostgreSQL, reading credentials from `.env`. |
| `src/load/load_data.py` | Loads the processed CSVs into PostgreSQL. Builds and loads dimension tables first, creates lookup mappings (country → key, date → key), then loads all fact tables using an upsert pattern (`row_hash` as conflict key) so re-running the pipeline doesn't create duplicate rows. Validates that no fact rows are missing a `country_key` or `date_key` before loading. |
| `postgresql/schema_n_resets/schema.sql` | DDL for all 9 tables, plus the 8 business-category schemas used by the analytical views. |
| `postgresql/schema_n_resets/reset_database.sql` | Drops all tables, used to reset the database to a clean state before a full pipeline re-run. |
| `postgresql/analytics/*.sql` | 8 files, one per business category (`sales`, `product`, `customer`, `geographic`, `cancellation`, `adjustment`, `non_sales`, `data_quality`), containing the 46 analytical views that power the Power BI dashboard. |
| `postgresql/analytics/saving_analytics.py` | Standalone backup script — re-runs each analytical view's query independently and exports the result to CSV under `data/analytics/`, so the underlying data behind every dashboard visual has a portable snapshot outside of Power BI/PostgreSQL. |
| `tests/test_environment.py` | Basic environment sanity check (confirms the database connection and required packages are set up correctly). |
| `notebooks/exploration.ipynb` | Exploratory analysis of the raw dataset — checking shape, missing values, data types, and duplicate rows, then prototyping and validating the transaction classification logic (sale/cancellation/adjustment/non-sale) and stock-code cleanup rules cell-by-cell before finalizing them in `transaction.py`. |

## Key Findings

### Revenue & Growth

![Total Revenue](assets/screenshots/sales_and_revenue.png)

Total revenue across the dataset (Dec 2010 – Dec 2011) came out to **$10,246,820.87** — see the [Dashboard Preview](#dashboard-preview) below for the full monthly trend.

### Product Performance

![Top 10 Products by Revenue](assets/screenshots/product_performance.png)

**"REGENCY CAKESTAND 3 TIER"** is the single highest-revenue product, narrowly ahead of "PAPER CRAFT, LITTLE BIRDIE" — though that second product turns out to also have the highest cancellation rate in the entire catalog (more on that below), which is a genuinely interesting tension worth digging into further.

### Customer Concentration

![Top 10% Revenue Concentration](assets/screenshots/customer_top_10_concentration.png)
![RFM Segment Breakdown](assets/screenshots/rfm_segment_donut.png)

Revenue is heavily concentrated: the **top 10% of customers generate 61.42%** of total revenue. Segmenting customers by purchase frequency and average order value shows the largest group (35.53%) falls into "Low Frequency and Low AOV" — meaning over a third of the customer base are low-value, infrequent buyers, while the smallest segment (14.47%) are frequent but low-spending customers.

### Cancellations

![Global Cancellation Rate](assets/screenshots/global_cancellation_rate_kpi.png)
![Highest Cancellation Rate Product](assets/screenshots/highest_cancellation_rate_product.png)

**14.81%** of all orders end in cancellation. At the product level, **"PAPER CRAFT, LITTLE BIRDIE" has a 50% cancellation rate** — half of every order containing this product gets cancelled, despite it being the second-highest revenue product in the catalog. That combination (high revenue, high cancellation) makes it a strong candidate for further investigation — is it a sizing/description issue, a stock reliability problem, or something else driving cancellations at that rate?

### Geographic Concentration

![UK Revenue Share](assets/screenshots/uk_revenue_share_kpi.png)

**85.14% of total revenue comes from the UK** alone, reflecting the dataset's origin as a UK-based retailer with limited but present international order volume.

### Data Quality

![Duplicate Cluster Size Distribution](assets/screenshots/duplicate_cluster_size_distribution.png)

After identifying and fixing an ETL sequencing bug (see [Engineering Challenges & Fixes](#engineering-challenges--fixes)), the validated duplicate transaction rate is **0.05%** — 280 duplicate rows across 98 clusters, mostly simple pairs. Before the fix, a stale flag from an earlier pipeline step had inflated this metric to **0.99%**, nearly 20x higher than the true rate.

## Engineering Challenges & Fixes

Each of these was caught through cross-validation — comparing totals against each other, sweeping for negative/null values, checking row counts against known-correct reference views — rather than by noticing something by chance while eyeballing rows. That process is what actually surfaced these, and it's worth calling out since "everything worked the first time" usually just means nobody checked closely enough.

### 1. Cancellation Quantity Sign Bug

**Symptom:** Cancellation-rate calculations were breaking. For "PAPER CRAFT , LITTLE BIRDIE," `total_sold` and `total_cancelled` came out to the exact same magnitude with opposite signs — 80,995 and -80,995 — which collapsed the rate's denominator to zero and returned NULL instead of a real percentage.

**Root cause:** In `transaction.py`, cancellation revenue is correctly derived from the original signed `Quantity` (negative, per the source dataset's convention), which is necessary — a cancellation should reduce total revenue. But `Quantity` itself was never separately normalized afterward, so the same negative sign needed for the revenue calculation also flowed into every `SUM(quantity)` aggregate meant to represent "units cancelled" — a count that should never be negative.

**Fix:**
```python
cancellations['revenue'] = cancellations['Quantity'] * cancellations['UnitPrice']
cancellations['Quantity'] = abs(cancellations['Quantity'])
```
Revenue is computed first from the signed value (preserving its correct negative impact on totals), and only afterward is `Quantity` converted to a positive magnitude. This fix was deliberately *not* applied to the adjustments table, since adjustment quantities are genuinely bidirectional (real inventory/account corrections go both ways), unlike cancellations, which are conceptually one-directional.

**Verification:**
```sql
SELECT description, total_sold, total_cancelled, unit_cancellation_rate
FROM cancellation.rates_by_product
WHERE description = 'PAPER CRAFT , LITTLE BIRDIE';
-- total_sold: 80,995 | total_cancelled: 80,995 | unit_cancellation_rate: 50.00

SELECT COUNT(*) FROM cancellation.products_by_volume WHERE cancelled_total < 0;
-- 0
```
The previously-broken product now resolves to a valid 50% cancellation rate, and no negative cancellation totals remain anywhere in the view.

### 2. Product Affinity Pairs Explosion

**Symptom:** `product.affinity_pairs` — meant to answer "which products are frequently bought together" — was unusable as a dashboard source due to sheer row count.

**Root cause:**
```sql
SELECT invoice_no, COUNT(DISTINCT stock_code) AS distinct_products
FROM fact_sales
GROUP BY invoice_no
ORDER BY distinct_products DESC
LIMIT 5;
```
573585 | 1108
581219 | 748
581492 | 730
580729 | 720
558475 | 703

A small number of extreme outlier invoices were driving a combinatorial explosion. Invoice `573585` alone had 1,108 distinct products — a self-join on that single invoice generates `n×(n-1)/2` candidate pairs, or roughly **613,000 pairs from one invoice**. These weren't normal customer baskets; they were bulk/wholesale-style orders skewing the self-join.

**Fix:** Filter out oversized invoices *before* the self-join runs, rather than filtering the results after:
```sql
WITH normal_invoices AS (
    SELECT invoice_no FROM fact_sales
    GROUP BY invoice_no
    HAVING COUNT(DISTINCT stock_code) <= 100
)
```
Combined with raising the co-occurrence threshold from `HAVING COUNT(...) >= 5` to `>= 20`, so "frequently bought together" reflects a statistically meaningful pattern rather than a handful of coincidental co-occurrences.

**Verification:**
```sql
SELECT COUNT(*) FROM product.affinity_pairs;
-- 42,326
```
Down from an unusable 1.5M+ rows to a dashboard-ready 42,326.

### 3. Duplicate-Flag ETL Sequencing Bug

**Symptom:** A `duplicate_group_count` distribution built while validating the Power BI dashboard showed something contradictory — thousands of rows flagged as "potential duplicates" had a group size of exactly 1. A cluster of size 1 isn't a cluster.

**Root cause:** In `transaction.py`, `IsPotentialDuplicateLine` was originally computed on the raw pre-dedup dataset, *then* exact duplicates were dropped afterward. Rows that were exact duplicates of each other also matched the narrower "potential duplicate" test (same invoice + stock code + quantity), so both got flagged. When one of the pair was removed during exact-duplicate cleanup, its surviving twin kept a stale "potential duplicate" flag from before the cleanup — even though its actual duplicate partner was already gone.

**Fix:**
```python
# Before: flag computed on raw data, before exact-dup removal
normalize_raw_transactions["IsExactDuplicate"] = normalize_raw_transactions.duplicated(keep='first')
clean_df = normalize_raw_transactions[normalize_raw_transactions['IsExactDuplicate'] == False].copy()

# After: flag computed on clean_df, AFTER exact-dup removal
clean_df["IsPotentialDuplicateLine"] = clean_df.duplicated(
    subset=['InvoiceNo','StockCode','Quantity'], keep=False
)
```
Reordering the two steps means the flag is now calculated only on data that's already been cleaned, so it reflects the true final group size.

**Verification:** Diagnosed with a window function comparing the stored flag against a freshly recalculated group size, confirming the mismatch before the fix. After re-running the pipeline, total flagged rows dropped from ~5,180 to **280**, spread across **98** distinct duplicate clusters — mostly simple pairs — correcting the dataset-wide duplicate rate from a misleading **0.99%** to an accurate **0.05%**.

### 4. Cancellation Rate by Country — Silent NULL Join Bug

**Symptom:** An earlier version of `cancellation.rates_by_country` used an `INNER JOIN` on the cancellations side, so any country with zero cancellations disappeared from the view entirely — not shown with a 0% rate, just silently absent. Switching to `LEFT JOIN` surfaced a second, subtler bug: the row now appeared, but with `country = NULL`.

**Root cause:**
```sql
LEFT JOIN dim_country AS dc ON uc.country_key = dc.country_key
```
Joining `dim_country` on `uc.country_key` (the cancellations side) breaks for zero-cancellation countries, since a `LEFT JOIN` with no match produces `NULL` for every cancellations-side column — including `country_key` — and `NULL = dc.country_key` can never evaluate true.

**Fix:** Join `dim_country` using the sales-side key instead, which is guaranteed non-null for every country:
```sql
LEFT JOIN dim_country AS dc ON us.country_key = dc.country_key
```

**Verification:**
```sql
SELECT COUNT(*) FROM cancellation.rates_by_country;  -- 38
SELECT COUNT(*) FROM geographic.revenue;              -- 38
```
Row counts now match exactly, confirming every country resolves to a real name with no silent NULLs or missing rows.

## Tech Stack

- **Python** — pandas for transformation, SQLAlchemy for database connectivity
- **PostgreSQL** — dimensional warehouse, 46 analytical views across 8 schemas
- **Power BI** — 8-page interactive dashboard, Import mode connected live to PostgreSQL
- **Jupyter Notebook** — exploratory data analysis and transformation logic prototyping
- **UCI Machine Learning Repository** — source dataset (Online Retail, id=352), fetched via `ucimlrepo`

## Setup / How to Run

### Prerequisites
- Python 3.10+
- PostgreSQL (running locally or accessible via connection string)
- Power BI Desktop (optional, only needed to view/rebuild the dashboard)

### 1. Clone and install dependencies
```bash
git clone https://github.com/Kgo890/retail-sales-etl-pipeline.git
cd retail-sales-etl-pipeline
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Set up environment variables
Create a `.env` file in the project root with your PostgreSQL connection details:
```
DATABASE_URL=postgresql+psycopg2://your_username:your_password@localhost:5432/retail_sales_db
```

### 3. Create the database schema
Run `postgresql/schema_n_resets/schema.sql` against your PostgreSQL database (via pgAdmin's Query Tool, or `psql`) to create all 9 tables and the 8 business-category schemas used by the analytical views.

### 4. Run the pipeline
```bash
python src/extract/dataset.py       # fetches raw data from UCI ML Repo
python src/transform/transaction.py # cleans, classifies, splits into fact tables
python src/load/load_data.py        # loads everything into PostgreSQL
```

### 5. Create the analytical views
Run each file in `postgresql/analytics/` against your database to create the 46 views (via pgAdmin or `psql`).

### 6. (Optional) Export analytics to CSV
```bash
python postgresql/analytics/saving_analytics.py
```
Produces a CSV snapshot of every analytical view under `data/analytics/`.

### 7. Open the dashboard
Open `powerbi/retail_pipeline.pbix` in Power BI Desktop and refresh the data connection to point to your local PostgreSQL instance.

## Dashboard Preview

The full dashboard is 8 pages, one per business-category schema. Three representative pages are shown below — the complete dashboard is available in `powerbi/retail_pipeline.pbix`.

### Sales & Revenue

![Sales & Revenue dashboard page](assets/screenshots/page_sales_revenue.png)

### Customer Analytics

![Customer Analytics dashboard page](assets/screenshots/page_customer_analytics.png)

### Data Quality

![Data Quality dashboard page](assets/screenshots/page_data_quality.png)