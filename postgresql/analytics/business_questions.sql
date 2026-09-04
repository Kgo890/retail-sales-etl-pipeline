-- What percentage of our total historical revenue is sitting with customers who haven't bought anything in over 90 days?
CREATE OR REPLACE VIEW sales.revenue_at_risk_summary AS 
WITH customer_behavior_summary AS (
    SELECT
    customer_id, 
    SUM(revenue) AS customer_lifetime_revenue,
    (SELECT MAX(full_date)::date FROM dim_date) AS global_snapshot_date,
    MAX(invoice_date)::date AS customer_last_purchase_date
    FROM fact_sales AS fs
    LEFT JOIN dim_date AS dd
    ON fs.date_key = dd.date_key
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
), 
revenue_segemntation AS  (
    SELECT 
    customer_lifetime_revenue,
    CASE WHEN (global_snapshot_date - customer_last_purchase_date) > 90 THEN customer_lifetime_revenue ELSE 0 END AS revenue_at_risk
    FROM customer_behavior_summary
)

SELECT 
SUM(customer_lifetime_revenue) AS grand_total_historical_reveune,
SUM(revenue_at_risk) AS absolute_dollars_at_risk,
ROUND(100.0 * (SUM(revenue_at_risk)/ NULLIF(SUM(customer_lifetime_revenue), 0)),2) As revenue_at_risk_percentage
FROM revenue_segemntation; 


-- Who are our "champions" that we can leverage for organic growth, 
-- and are our "at-risk" high value buyers who need a discount intervention right now 
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



-- What is the average order value (AOV) drop-off velocity as a customer transitions from active to hibernating?
CREATE OR REPLACE VIEW customer.aov_dropoff_velocity AS 
WITH customer_metric AS (
    SELECT 
    customer_id,
    SUM(revenue) AS grand_total_historical_reveune,
    COUNT(DISTINCT invoice_no) As customers_orders, 
    (SELECT MAX(full_date)::date FROM dim_date) AS global_snapshot_date,
    MAX(invoice_date)::date AS customer_last_purchase_date
    FROM fact_sales
    GROUP BY customer_id
),
customer_inactve_targets AS (
SELECT 
ROUND((grand_total_historical_reveune / customers_orders),2) AS customer_aov,
CASE 
WHEN (global_snapshot_date - customer_last_purchase_date) <= 30 THEN 'Active Tier'
WHEN (global_snapshot_date - customer_last_purchase_date) <= 60 THEN 'Cooling Tier'
WHEN (global_snapshot_date - customer_last_purchase_date) <= 90 THEN 'Slipping Tier'
ELSE 
'Hibernating Tier' END AS inactive_targets
FROM customer_metric
)
SELECT
inactive_targets,
ROUND(AVG(customer_aov),2) AS global_tier_aov
FROM customer_inactve_targets
GROUP BY inactive_targets
ORDER BY 
CASE 
WHEN inactive_targets = 'Active Tier' THEN 1
WHEN inactive_targets = 'Cooling Tier' Then 2
WHEN inactive_targets = 'Slipping Tier' Then 3
ELSE 4
END; 

-- which products have the highest cancellation rate
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
