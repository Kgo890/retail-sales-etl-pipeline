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