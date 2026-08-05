-- which countries generate the most revenue
    CREATE OR REPLACE VIEW geographic.revenue AS 
    SELECT dc.country, SUM(fs.revenue) AS total_revenue
    FROM fact_sales AS fs
    INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
    GROUP BY dc.country;

-- countries with high order volume
    CREATE OR REPLACE VIEW geographic.order_volumes AS
    SELECT dc.country, COUNT(DISTINCT fs.invoice_no) AS order_volume
    FROM fact_sales AS fs
    INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
    GROUP BY dc.country;

-- which countries have the highest average order value
    CREATE OR REPLACE VIEW geographic.high_aov AS 
    SELECT dc.country, 
    ROUND(SUM(fs.revenue)/COUNT(DISTINCT fs.invoice_no),2) AS average_order_value
    FROM fact_sales AS fs
    INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
    GROUP BY dc.country
    HAVING COUNT(DISTINCT fs.invoice_no) >= 10;

-- which countries have many orders but low average order value
    CREATE OR REPLACE VIEW geographic.high_volume_low_aov AS
    SELECT dc.country, 
    COUNT(DISTINCT fs.invoice_no) AS order_volume, 
    ROUND(SUM(fs.revenue)/COUNT(DISTINCT fs.invoice_no) ,2) AS average_order_value
    FROM fact_sales AS fs
    INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
    GROUP BY dc.country
    HAVING COUNT(DISTINCT fs.invoice_no) > 50;

-- which countries with fewer orders and high average order value
    CREATE OR REPLACE VIEW geographic.low_volume_high_aov AS
    SELECT dc.country, 
    COUNT(DISTINCT fs.invoice_no) AS order_volume, 
    ROUND(SUM(fs.revenue)/COUNT(DISTINCT fs.invoice_no),2) AS average_order_value
    FROM fact_sales AS fs
    INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
    GROUP BY dc.country
    HAVING COUNT(DISTINCT fs.invoice_no) BETWEEN 10 AND 50;

-- what percentage of total revenue comes from each country
    CREATE OR REPLACE VIEW geographic.revenue_share AS 
    WITH product_by_country AS (
        SELECT dc.country, SUM(fs.revenue) AS total_revenue_per_country
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        GROUP BY dc.country
    ),
    total_revenue AS (
        SELECT SUM(fs.revenue) AS total_revenue
        FROM fact_sales AS fs
    )
    SELECT country, ROUND((pbc.total_revenue_per_country/t.total_revenue) * 100,2) AS percentage
    FROM product_by_country AS pbc
    CROSS JOIN total_revenue AS t;

-- which countries have the highest revenue per customer 
    CREATE OR REPLACE VIEW geographic.revenue_per_customer AS
    SELECT dc1.country, 
    SUM(fs.revenue) AS total_revenue, 
    COUNT(DISTINCT fs.customer_id) AS number_of_customers,
    ROUND((SUM(fs.revenue)/COUNT(DISTINCT fs.customer_id)),2) AS revenue_per_customer
    FROM fact_sales AS fs
    INNER JOIN dim_country AS dc1 ON fs.country_key = dc1.country_key
    GROUP BY dc1.country
    HAVING COUNT(DISTINCT fs.customer_id) > 10;

-- which countries are growing or declining over time 
    CREATE OR REPLACE VIEW geographic.growth_trends AS 
    WITH timeline AS (
        SELECT 
        dc.country,
        dd.year,
        dd.month,
        dd.month_name,
        SUM(fs.revenue) AS current_revenue
        FROM fact_sales as fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        GROUP BY dc.country,dd.year,dd.month,dd.month_name
    ),
    grab_revenue AS(
        SELECT 
        country,
        year,
        month,
        month_name,
        current_revenue,
        LAG(current_revenue) OVER(PARTITION BY country ORDER BY year, month) AS previous_revenue
        FROM timeline
    ), 
    monthly_growth AS (

    SELECT 
    country,
    year,
    month_name,
    current_revenue,
    previous_revenue,
   ROUND((((current_revenue - previous_revenue)
    / NULLIF(previous_revenue, 0)) * 100), 2) AS growth_percentage
    FROM grab_revenue
    WHERE previous_revenue IS NOT NULL
    )
    SELECT 
    country,
    ROUND(AVG(growth_percentage), 2) AS avg_monthly_growth_rate,
    COUNT(CASE WHEN growth_percentage > 0 THEN 1 END) AS months_of_growth,
    COUNT(CASE WHEN growth_percentage < 0 THEN 1 END) AS months_of_decline
    FROM monthly_growth
    GROUP BY country;
