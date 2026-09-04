# Direct-to-Consumer (DTC) Customer Churn Diagnostic & Revenue Leakage Audit

An end-to-end data analytics and engineering asset that audits **$8.74M** in historical transactional data to isolate customer retention decay patterns, partition high-value consumer behavior cohorts, and expose critical product fulfillment failures.

---

## Executive Summary: The Business Crisis
In direct-to-consumer (DTC) retail operations, front-end acquisition volume can frequently mask critical operational degradation. While a business may celebrate stable gross sales, silent customer churn and hidden backend processing leaks heavily erode customer lifetime value (LTV) and inflate Customer Acquisition Costs (CAC). 

This project addresses this exact strategic blind spot. By auditing **$8.74M** in raw historical transaction records, this analysis reveals that **11.64% ($1.02M)** of total enterprise revenue is trapped in stagnant customer accounts that have completely ceased activity for over 90 days. Furthermore, an operational quality audit exposed massive revenue bleeding points, isolating specific high-velocity inventory lines suffering from complete **100.00% operational cancellation failure rates** previously obscured by basic aggregated data bugs.

### Core Corporate Key Performance Indicators (KPIs)
* **Total Gross Historical Revenue:** $8.74M
* **Revenue at Risk (Inactivity > 90 Days):** 11.64% ($1.02M)
* **Active Revenue Portfolio Management:** 88.36% ($7.72M)

---

##  Business Intelligence Canvas & Dashboard Layout
The underlying analytics models are brought to life through a centralized, 1-page executive control dashboard in Power BI. The reporting layer is structured into three highly scannable control quadrants designed to drive immediate management intervention:

### 1. Executive KPI Row
Clean, high-impact scorecard indicators providing instant, top-line visibility into total company capital exposure in under 2 seconds.
![Executive KPI Row](powerbi/executive%20KPI%20Row.png)

### 2. Customer Retention & Churn Dynamics
An interactive line graph tracking the chronological AOV velocity curve linked directly to a categorical customer marketplace treemap. This layout allows stakeholders to cross-filter the entire page by clicking individual behavioral risk segments.
![Customer Retention & Churn Dynamics](powerbi/Customer%20Retention%20%26%20Churn%20Dynamics.png)

#### Detailed At-Risk Customer Segment Analysis
Drilling directly into the RFM framework isolates the exact unique account profiles (such as Customer ID `17850`) that represent high-value retention targets for marketing campaigns.  

![At-Risk Customer Segment](powerbi/At-risk-customer.png)

### 3. Operations Risk & Item Diagnostics
A flat, auto-fitting data grid sorting inventory items by cancellation severity, exposing deep supply chain bleeding points.
![Operations Risk & Item Diagnostics](powerbi/Operation%20Risk%20%26%20Item%20Diagnostics.png)

### Complete Dashboard Composition Overview
The unified interactive canvas aggregates all data streams into a single corporate view to protect stakeholder scannability.
![Full Dashboard Layout](powerbi/full_dashboard.png)

---

## Strategic Business Directives & Core Questions Answered

### Directive 1: Quantifying Revenue At Risk
* **The Business Question:** What percentage of our total historical revenue is sitting with customers who haven't bought anything in over 90 days?
* **The Analytics Strategy:** To handle customer lifecycle clocks on a static historical dataset without real-time dates marking 100% of accounts as stale, a global snapshot anchor was dynamically computed using the maximum available date in `dim_date`. Accounts were evaluated at the individual account level by measuring the variance between their absolute latest transaction timestamp and the global snapshot anchor.
* **Strategic Finding:** Exactly **11.64% ($1.02M)** of total historical revenue belongs to stale accounts inactive for over 90 days. 
* **Corporate Decision Impact:** This finding disproves the assumption that front-end customer acquisition is stable. It justifies an immediate strategic pivot away from expensive, high-CAC paid acquisition channels, transferring capital into automated backend email retention triggers to reactivate stale high-value accounts.

### Directive 2: VIP Customer Segmentation via RFM Modeling
* **The Business Question:** Who are our "Champions" to leverage for organic growth, and who are our "At-Risk" high-value buyers requiring immediate discount interventions?
* **The Analytics Strategy:** Engineered a global multi-dimensional scaling matrix using PostgreSQL window aggregates (`NTILE(5)`) to partition the entire customer directory into equal 20% percentiles based on Recency, Frequency, and Monetary parameters. 
* **Segment Definitions:** 
  * *Champions:* Bottom-line anchors purchasing frequently, spending heavily, and ordering very recently (RFM: 5-5-5, 5-4-5).
  * *At-Risk High-Value:* Historical VIP accounts who spent massive capital frequently but have completely ceased activity (RFM: 1-5-5, 2-5-5).
* **Corporate Decision Impact:** Isolates specific high-priority user profiles out of thousands of low-value, single-purchase accounts. This enables marketing teams to deploy hyper-targeted discount campaigns exclusively to slipping VIP spenders, maximizing marketing ROI.

### Directive 3: Average Order Value (AOV) Drop-Off Velocity
* **The Business Question:** What is the average order value (AOV) decay curve as a customer transitions from active to fully hibernating?
* **The Analytics Strategy:** Segmented total transactions into four distinct chronological horizons based on days-aged inactivity windows, tracking collective order size health (`SUM(revenue) / COUNT(DISTINCT invoice_no)`).
* **Velocity Metrics:**
  * *Active Tier (0-30 Days Inactive):* $435.40 AOV (Baseline)
  * *Cooling Tier (31-60 Days Inactive):* $388.95 AOV
  * *Slipping Tier (61-90 Days Inactive):* $429.89 AOV
  * *Hibernating Tier (91+ Days Inactive):* $401.88 AOV
* **Strategic Finding:** Tracking the trend line exposed an immediate **10.67% drop** in transaction sizes as buyers move from active to cooling stages. Crucially, a behavioral spike was discovered in the Slipping Tier ($429.89), proving that slipping customers make a large "parting purchase" before completely ghosting the platform.
* **Corporate Decision Impact:** Establishes the exact operational threshold for automated retention workflows. Win-back sequences must be triggered precisely between days 30 and 60 to counteract the initial 10.67% spending drop before accounts enter late-stage decay.

### Directive 4: Operational Product Quality & Cancellation Audit
* **The Business Question:** Which inventory items suffer from the highest cancellation rates, indicating supplier defects or backend checkout anomalies?
* **The Analytics Strategy:** Constructed a cross-schema relational view joining aggregated sales and cancellation tables. Unit cancellation velocity was calculated directly against the gross baseline volume requested (`ps.total_sold`) to accurately measure performance leakage without double-counting anomalies.
* **Fulfillment Failure Case Studies:** 
  * Deep-table auditing flagged severe transaction anomalies across high-volume items. The database tracked exactly **80,995 units ordered** for `PAPER CRAFT, LITTLE BIRDIE` alongside exactly **80,995 units cancelled**, revealing a **100.00% complete failure rate**.
  * Severe drops were also isolated for `ROTATING SILVER ANGELS T-LIGHT HLDR` at a **99.10% cancellation rate** (9,376 units cancelled out of 9,461 ordered) and `MEDIUM CERAMIC TOP STORAGE JAR` at a **95.46% cancellation rate** (74,494 units cancelled out of 78,033 ordered).
* **Corporate Decision Impact:** These extreme patterns signal critical automated B2B checkout failure loops, bulk-order system processing bugs, or severe upstream supplier inventory collapses where massive bulk orders had to be entirely force-revoked by the system.

---

##  Technical Architecture & Schema Design
To protect enterprise reporting speed, optimize analytical queries, and enforce clear security access controls, the database is architected with a multi-schema relational model in PostgreSQL, breaking entirely away from standard single-schema (`public`) clutter.

```text
UCI ML Repo — Online Retail Dataset (id=352)
                │
                ▼
Extract (Python / ucimlrepo API) -> Raw CSV
                │
                ▼
Transform (Python / pandas object parsing & classification) -> Processed CSVs
                │
                ▼
PostgreSQL Production Star Schema
    ├── Dimensional Tables (`dim_product`, `dim_customer`, `dim_country`, `dim_date`)
    └── Partitioned Fact Tables (`fact_sales`, `fact_cancellations`, `fact_adjustment`, `fact_non_sale`)
                │
                ▼
Analytical Layer (Isolated Schema Namespaces)
    ├── customer.*  │  sales.*  │  cancellation.*  │  product.*
                │
                ▼
Production Database Views (Semantic Reporting Layer)
                │
                ▼
1-Page Power BI Executive Control Dashboard
```

### Reporting Layer Isolation Strategy
* **`sales` Schema:** Houses transaction logs (`fact_sales`) tracking clean gross sales.
* **`customer` Schema:** Manages user metadata (`dim_customer`) and customer-level analytical views.
* **`cancellation` Schema:** Isolates broken, revoked, or returned transactions (`fact_cancellations`) to prevent canceled orders from skewing active revenue trends.
* **`product` & `geographic` Schemas:** Store dimensions optimizing inventory items and regional demographic profiles.

---

## 🛠️ Data Diagnostics & Production SQL Views

### 1. The Production Order-Cancellation Metric Correction View
An earlier iteration of this database view contained a structural formula error where the denominator double-counted quantities by adding sales and cancellations together (ps.total_sold + pc.total_cancelled), masking the true scale of the problem as a 50% metric. The production-ready script below addresses the bug, correctly evaluating cancellations against initial gross order volumes to yield the accurate 100.00% complete failure metric:

CREATE OR REPLACE VIEW cancellation.rates_by_product AS
    WITH product_sales AS (
    SELECT 
        dp.stock_code,
        dp.description,
        SUM(fs.quantity) AS total_sold
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
    GROUP BY dp.stock_code, dp.description
    ),
    product_cancellations AS (
    SELECT 
        stock_code,
        SUM(quantity) AS total_cancelled
    FROM fact_cancellations
    GROUP BY stock_code
    )
    SELECT 
    ps.description,
    ps.total_sold,
    COALESCE(pc.total_cancelled, 0) AS total_cancelled,
    ROUND(
        (COALESCE(pc.total_cancelled, 0)::NUMERIC / 
        NULLIF(
            ps.total_sold,
            0
        )) * 100, 
        2
    ) AS unit_cancellation_rate
    FROM product_sales AS ps
    LEFT JOIN product_cancellations AS pc ON ps.stock_code = pc.stock_code
    WHERE ps.total_sold > 50;

## 2. The Multi-Spaced RFM Customer Segmentation View
This analytical view implements an automated account sorting pipeline, ranking and categorizing accounts into clean strategic labels based on global enterprise performance benchmarks:

CREATE OR REPLACE VIEW customer.rfm_segment_rankings AS 
WITH customer_metrics AS (
    SELECT 
    customer_id,
    SUM(revenue) AS grand_total_historical_reveune,
    COUNT(DISTINCT invoice_no) As customers_orders, 
    (SELECT MAX(full_date)::date FROM dim_date) AS global_snapshot_date,
    MAX(invoice_date)::date AS customer_last_purchase_date
    FROM fact_sales
    GROUP BY customer_id
), 
ranking AS (
SELECT 
customer_id,
grand_total_historical_reveune,
NTILE(5) OVER (
    ORDER BY (global_snapshot_date - customer_last_purchase_date) DESC
) AS recency,
NTILE(5) OVER (
    ORDER BY customers_orders ASC
) AS frequency,
NTILE(5) OVER (
    ORDER BY grand_total_historical_reveune ASC
) As monetary
FROM customer_metrics
)

SELECT 
customer_id,
recency,
frequency,
monetary,
CASE 
WHEN recency >=4 AND frequency  >= 4 AND monetary >= 4 THEN 'Champion'
WHEN recency <= 2 AND frequency >= 4 AND monetary >= 4 THEN 'At-Risk High Value'
WHEN recency <= 2 AND frequency <= 2 AND monetary <= 2 THEN 'Hibernating Low Value'
ELSE 'Other Account'
END AS segmentation_labels
FROM ranking

# Setup & Local Deployment
## 1. Environment Configuration
Clone the repository and create a .env file in the root directory:env DB_HOST=127.0.0.1 DB_PORT=5432 DB_NAME=retail_sales_db DB_USER=postgres DB_PASSWORD=your_secure_password 

## 2. Pipeline Execution & Object Deployment
```bash
Initialize virtual environment and install data packages

python -m venv venv
source venv/bin/activat
epip install -r requirements.txt

Run pipeline to deploy tables, schemas, and analytical views

python postgresql/schema_n_resets/reset_database.py
python -m src.extract.datasetpython -m src.transform.transaction
python -m src.load.load_data

``` 
