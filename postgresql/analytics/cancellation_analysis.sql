-- products with the most cancel orders
    CREATE OR REPLACE VIEW cancellation.products_by_orders AS
    SELECT dp.description, COUNT(DISTINCT fc.invoice_no) AS cancelled_orders
    FROM fact_cancellations AS fc
    INNER JOIN dim_product AS dp ON fc.stock_code = dp.stock_code
    GROUP BY dp.description; 

-- what percentage of orders are cancellations 
    CREATE OR REPLACE VIEW cancellation.global_rate AS 
    SELECT 
    (SELECT COUNT(DISTINCT invoice_no) FROM fact_sales) AS total_sales_orders,
    (SELECT COUNT(DISTINCT invoice_no) FROM fact_cancellations) AS total_cancelled_orders,
    ROUND(
        ((SELECT COUNT(DISTINCT invoice_no) FROM fact_cancellations)::NUMERIC / 
        ((SELECT COUNT(DISTINCT invoice_no) FROM fact_sales) + (SELECT COUNT(DISTINCT invoice_no) FROM fact_cancellations))) * 100, 
        2
    ) AS cancellation_percentage;

-- which products are cancelled most frequently
    CREATE OR REPLACE VIEW cancellation.products_by_volume AS 
    SELECT dp.description,SUM(fc.quantity) AS cancelled_total
    FROM fact_cancellations AS fc
    LEFT JOIN dim_product AS dp ON fc.stock_code = dp.stock_code
    GROUP BY dp.description;

-- which countries have the highest cancellations rates
    CREATE OR REPLACE VIEW cancellation.rates_by_country AS
    WITH unique_sales AS (
        SELECT country_key,COUNT(DISTINCT invoice_no) AS total_sales
        FROM fact_sales
        GROUP BY country_key
    ),
    unique_cancellations AS (
        SELECT country_key,COUNT(DISTINCT invoice_no) AS total_cancels
        FROM fact_cancellations
        GROUP BY country_key
    )

    SELECT 
    dc.country,
    us.total_sales,
    COALESCE(uc.total_cancels, 0) AS total_cancels,
    ROUND(
        COALESCE(uc.total_cancels, 0)::NUMERIC 
        / (us.total_sales + COALESCE(uc.total_cancels, 0)) * 100, 
    2) AS cancellation_rate
    FROM unique_sales AS us
    LEFT JOIN unique_cancellations AS uc ON us.country_key = uc.country_key
    LEFT JOIN dim_country AS dc ON us.country_key = dc.country_key;

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
            ps.total_sold + COALESCE(pc.total_cancelled, 0),
            0
        )) * 100, 
        2
    ) AS unit_cancellation_rate
    FROM product_sales AS ps
    LEFT JOIN product_cancellations AS pc ON ps.stock_code = pc.stock_code
    WHERE ps.total_sold > 50;

-- is cancellation rate increasing or decreasing over time
    CREATE OR REPLACE VIEW cancellation.trends_over_time AS
    WITH monthly_sales AS (
        SELECT dd.year, dd.month, dd.month_name, COUNT(DISTINCT fs.invoice_no) AS sales_count
        FROM fact_sales AS fs
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        GROUP BY dd.year, dd.month, dd.month_name
    ),
    monthly_cancels AS (
        SELECT dd.year, dd.month, COUNT(DISTINCT fc.invoice_no) AS cancels_count
        FROM fact_cancellations AS fc
        INNER JOIN dim_date AS dd ON fc.date_key = dd.date_key
        GROUP BY dd.year, dd.month
    )
    SELECT 
        ms.year,
        ms.month_name,
        ms.sales_count,
        COALESCE(mc.cancels_count, 0) AS cancels_count,
        ROUND(
            COALESCE(mc.cancels_count, 0)::NUMERIC 
            / NULLIF(ms.sales_count + COALESCE(mc.cancels_count, 0), 0) * 100,
            2
        ) AS cancellation_rate,
        ms.month,
        (ms.year * 100 + ms.month) AS year_month_sort,
        LEFT(ms.month_name, 3) || ' ' || ms.year AS month_year_label
    FROM monthly_sales AS ms
    LEFT JOIN monthly_cancels AS mc ON ms.year = mc.year AND ms.month = mc.month;

-- do high revenue products also have high cancellation rates 
    CREATE OR REPLACE VIEW cancellation.high_revenue_risk_matrix AS
    WITH product_perf AS (
    SELECT 
        dp.stock_code,
        dp.description,
        SUM(fs.revenue) AS total_revenue,
        SUM(fs.quantity) AS total_sold
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp 
        ON fs.stock_code = dp.stock_code
    GROUP BY dp.stock_code, dp.description
    ),
    product_cancels AS (
        SELECT 
            stock_code,
            SUM(quantity) AS total_cancelled
        FROM fact_cancellations
        GROUP BY stock_code
    ),
    product_metrics AS (
        SELECT
            pp.stock_code,
            pp.description,
            pp.total_revenue,
            pp.total_sold,
            COALESCE(pc.total_cancelled, 0) AS total_cancelled,
            ROUND(
                COALESCE(pc.total_cancelled, 0)::NUMERIC
                /
                NULLIF(
                    pp.total_sold + COALESCE(pc.total_cancelled, 0),
                    0
                ) * 100,
                2
            ) AS cancellation_rate
        FROM product_perf AS pp
        LEFT JOIN product_cancels AS pc
            ON pp.stock_code = pc.stock_code
    ),
    product_segments AS (
        SELECT
            *,
            NTILE(4) OVER (
                ORDER BY total_revenue DESC
            ) AS revenue_tier,
            NTILE(4) OVER (
                ORDER BY cancellation_rate DESC
            ) AS cancellation_tier
        FROM product_metrics
    )
    SELECT
        description,
        total_revenue,
        total_sold,
        total_cancelled,
        cancellation_rate
    FROM product_segments
    WHERE revenue_tier = 1;
