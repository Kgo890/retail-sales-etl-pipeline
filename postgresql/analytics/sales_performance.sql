-- how much revenue did the business generate over time 

-- total revenue sales
CREATE OR REPLACE VIEW sales.total_revenue AS 
SELECT SUM(revenue) AS total_sales_revenue
FROM fact_sales;

-- revenue by month 
CREATE OR REPLACE VIEW sales.revenue_by_month AS 
SELECT dd.month_name, SUM(fs.revenue) AS total_sales_revenue, dd.month
FROM fact_sales AS fs
INNER JOIN dim_date AS dd
ON fs.date_key = dd.date_key
GROUP BY dd.month, dd.month_name;

--revenue by year and month
CREATE OR REPLACE VIEW sales.revenue_by_year_n_month AS 
SELECT dd.year,dd.month_name, SUM(fs.revenue) AS total_sales_revenue, dd.month
FROM fact_sales AS fs
INNER JOIN dim_date AS dd
ON fs.date_key = dd.date_key
GROUP BY dd.year, dd.month, dd.month_name;

-- revenue growth or decline 
CREATE OR REPLACE VIEW sales.revenue_trends AS 
WITH months_revenue AS (
    SELECT dd.year,
    dd.month,
    dd.month_name,
    SUM(fs.revenue) AS monthly_revenue
    FROM fact_sales AS fs
    INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
    GROUP BY dd.year, dd.month, dd.month_name
)
SELECT 
    year, month_name, monthly_revenue,
    LAG(monthly_revenue) OVER (ORDER BY year, month) AS prior_month_revenue,
    ROUND(
    100.0 * (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY year,month))
    / NULLIF(LAG(monthly_revenue) OVER (ORDER BY year,month), 0),
    2
    ) AS mom_growth_pct,
    month,
    (year * 100 + month) AS year_month_sort,
    LEFT(month_name, 3) || ' ' || year AS month_year_label
FROM months_revenue;


 -- which months had the highest and lowest sales
CREATE OR REPLACE VIEW sales.monthly_sales_performance AS 
SELECT 
dd.year, 
dd.month_name, 
SUM(fs.revenue) AS total_sales_revenue, 
COUNT(fs.invoice_no) AS number_of_transactions ,
SUM(fs.quantity) AS total_items_sold,
dd.month
FROM fact_sales as fs
INNER JOIN dim_date as dd
ON fs.date_key = dd.date_key
GROUP BY dd.year, dd.month, dd.month_name;


