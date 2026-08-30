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
