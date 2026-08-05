-- who are the highest-value customers

-- total customer revenue
    CREATE OR REPLACE VIEW customer.revenue_summary AS
    SELECT dc.customer_id, 
    SUM(fs.revenue) AS total_customer_revenue
    FROM fact_sales as fs
    INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id 
    GROUP BY dc.customer_id;

-- number of purchases
    CREATE OR REPLACE VIEW customer.order_counts AS
    SELECT dc.customer_id, COUNT(DISTINCT(fs.invoice_no)) AS number_of_orders
    FROM fact_sales AS fs
    INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
    GROUP BY dc.customer_id;


-- average order value
    CREATE OR REPLACE VIEW customer.average_order_value AS
    SELECT dc.customer_id, 
    ROUND(SUM(fs.revenue)/COUNT(DISTINCT(fs.invoice_no)),2) AS average_order_value
    FROM fact_sales AS fs 
    INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
    GROUP BY dc.customer_id;

-- purchase frequency 
    CREATE OR REPLACE VIEW customer.purchase_frequency AS
    SELECT 
    dc.customer_id,
    COUNT(DISTINCT fs.invoice_no) AS total_orders,
    COUNT(DISTINCT (dd.date_key / 100)) AS active_months,
    ROUND(
        COUNT(DISTINCT fs.invoice_no) * 1.0 
        / COUNT(DISTINCT (dd.date_key/100)), 2
        ) AS monthly_purchase_frequency
    FROM fact_sales AS fs 
    INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
    INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
    GROUP BY dc.customer_id;


-- how concentrated is revenue among customers

-- what percentage of total revenue from the top 10% of customer?
    CREATE OR REPLACE VIEW customer.revenue_concentration AS
    WITH customer_revenue AS (
        SELECT dc.customer_id, 
        SUM(fs.revenue) AS total_customer_revenue
        FROM fact_sales AS fs 
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        GROUP BY dc.customer_id
    ),
    customer_deciles AS (
        SELECT 
        total_customer_revenue,
        NTILE(10) OVER (ORDER BY total_customer_revenue DESC) AS decile
        FROM customer_revenue
    )

    SELECT 
        ROUND(SUM(CASE WHEN decile = 1 THEN total_customer_revenue ELSE 0 END),2) AS top_10_percent_revenue,
        ROUND(SUM(total_customer_revenue),2) AS grand_total_revenue,
        ROUND(100.0 * SUM(CASE WHEN decile = 1 THEN total_customer_revenue ELSE 0 END) / SUM(total_customer_revenue),2) AS percentage_of_total_revenue
    FROM customer_deciles; 


-- What is the average number of orders per active customer each month?
    CREATE OR REPLACE VIEW customer.monthly_order_averages AS
    SELECT dd.year,
    dd.month_name,
    COUNT(DISTINCT fs.invoice_no) AS total_orders,
    COUNT(DISTINCT dc.customer_id) AS active_customers,
    ROUND(
        COUNT(DISTINCT fs.invoice_no) * 1.0
        / COUNT(DISTINCT dc.customer_id),
        2) AS avg_order_per_customer
    FROM fact_sales AS fs
    INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
    INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
    GROUP BY dd.year,dd.month,dd.month_name;


-- Who are our high-frequency vs.high-AOV customers?
    CREATE OR REPLACE VIEW customer.rfm_segments AS
    WITH metrics_per_customer AS (
        SELECT 
        dc.customer_id,
        SUM(fs.revenue) AS total_revenue,
        COUNT(DISTINCT fs.invoice_no) AS total_orders,
        COUNT(DISTINCT (dd.date_key / 100)) AS active_months,
        ROUND(COUNT(DISTINCT fs.invoice_no) * 1.0/COUNT(DISTINCT (dd.date_key/ 100)),2) AS purchase_frequency,
        ROUND(SUM(fs.revenue) * 1.0 / COUNT(DISTINCT fs.invoice_no),2) AS average_order_value
        FROM fact_sales AS fs
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        GROUP BY dc.customer_id
    ),

    segment_metrics AS (
        SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_frequency) AS median_frequency,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY average_order_value) AS median_aov
        FROM metrics_per_customer
    )
    SELECT 
    m.customer_id, 
    m.purchase_frequency, 
    m.average_order_value,
    CASE WHEN m.purchase_frequency > sm.median_frequency AND m.average_order_value > sm.median_aov
            THEN 'High Frequency and High AOV'
    WHEN m.purchase_frequency <= sm.median_frequency AND m.average_order_value > sm.median_aov
            THEN 'Low Frequency and High AOV'
    WHEN m.purchase_frequency > sm.median_frequency AND m.average_order_value <= sm.median_aov
            THEN 'High Frequency and Low AOV'
    ELSE 'Low Frequency and Low AOV'
    END AS customer_segment
    FROM metrics_per_customer AS m
    CROSS JOIN segment_metrics AS sm;



