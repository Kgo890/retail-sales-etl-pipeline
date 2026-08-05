    CREATE OR REPLACE VIEW product.sales_summary AS 
    SELECT
    fs.stock_code,
    dp.description,
    SUM(fs.revenue) AS total_sales_revenue,
    SUM(fs.quantity) AS total_quantity_sold,
    COUNT(fs.invoice_no) AS total_number_transactions
    FROM fact_sales as fs
    LEFT JOIN dim_product as dp ON fs.stock_code = dp.stock_code
    GROUP BY fs.stock_code, dp.description;

-- which frequently purchased products generate the lowest revenue per purchase?
   CREATE OR REPLACE VIEW product.frequent_low_revenue_per_purchase AS
   WITH product_stats AS (
        SELECT 
            dp.stock_code,
            dp.description,
            COUNT(DISTINCT fs.invoice_no) AS purchase_frequency,
            SUM(fs.revenue) AS total_revenue
        FROM fact_sales AS fs
        INNER JOIN dim_product AS dp 
            ON fs.stock_code = dp.stock_code
        GROUP BY dp.stock_code, dp.description
    )
    SELECT 
        description,
        purchase_frequency,
        ROUND(
            (total_revenue / NULLIF(purchase_frequency, 0))::NUMERIC,
            2
        ) AS revenue_per_purchase,
        ROUND(total_revenue::NUMERIC, 2) AS total_revenue
    FROM product_stats;

-- which products generate high revenue despite low sales volume
    CREATE OR REPLACE VIEW product.high_revenue_low_volume_manual AS 
    WITH product_stats AS (
    SELECT 
        dp.stock_code,
        dp.description,
        SUM(fs.quantity) AS total_volume,
        SUM(fs.revenue) AS total_revenue
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp 
        ON fs.stock_code = dp.stock_code
    GROUP BY dp.stock_code, dp.description
    )
    SELECT 
        description,
        total_volume,
        ROUND(total_revenue::NUMERIC, 2) AS total_revenue
    FROM product_stats
    WHERE total_volume <= 56
    AND total_revenue >= 2220.02;


-- Which products have high sales volume but low revenue?
    CREATE OR REPLACE VIEW product.high_volume_low_revenue_quadrant AS 
    WITH product_stats AS (
    SELECT 
        dp.description,
        SUM(fs.quantity) AS total_volume,
        SUM(fs.revenue) AS total_revenue
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
    GROUP BY dp.description
    ),
    segment_products AS (
        SELECT
            description,
            total_volume,
            total_revenue,
            NTILE(4) OVER (ORDER BY total_volume DESC) AS volume_tier,   
            NTILE(4) OVER (ORDER BY total_revenue ASC) AS revenue_tier
        FROM product_stats
    )
    SELECT 
        description,
        total_volume,
        total_revenue
    FROM segment_products
    WHERE volume_tier = 1 
    AND revenue_tier = 1;

-- Which products generate high revenue despite low sales volume?
    CREATE OR REPLACE VIEW product.high_revenue_low_volume_quadrant AS 
    WITH product_stats AS (
    SELECT 
        dp.description,
        SUM(fs.quantity) AS total_volume,
        SUM(fs.revenue) AS total_revenue
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
    GROUP BY dp.description
    ),
    segment_products AS (
        SELECT
            description,
            total_volume,
            total_revenue,
            NTILE(4) OVER (ORDER BY total_volume ASC) AS volume_tier,     
            NTILE(4) OVER (ORDER BY total_revenue DESC) AS revenue_tier 
        FROM product_stats
    )
    SELECT 
        description,
        total_volume,
        total_revenue
    FROM segment_products
    WHERE volume_tier = 1 
    AND revenue_tier = 1;

-- Which products are consistently popular over time?
    CREATE OR REPLACE VIEW product.consistency_trends AS
    SELECT 
    dp.description,
    COUNT(DISTINCT (dd.year || '-' || dd.month)) AS unique_months_active,
    SUM(fs.quantity) AS total_units_sold
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
    INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
    GROUP BY dp.description;

-- Which products are declining in sales?
    CREATE OR REPLACE VIEW product.sales_decline AS 
    WITH dataset_range AS (
    SELECT 
        MIN(dd.full_date) AS start_date,
        MAX(dd.full_date) AS end_date,
        MIN(dd.full_date) + (MAX(dd.full_date) - MIN(dd.full_date)) / 2 AS midpoint_date
    FROM fact_sales AS fs
    INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
    ),
    time_period AS (
        SELECT 
            dp.description,
            SUM(CASE WHEN dd.full_date <= dr.midpoint_date THEN fs.quantity ELSE 0 END) AS first_half_sales,
            SUM(CASE WHEN dd.full_date > dr.midpoint_date THEN fs.quantity ELSE 0 END) AS second_half_sales
        FROM fact_sales AS fs
        INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        CROSS JOIN dataset_range AS dr
        GROUP BY dp.description
    )
    SELECT 
        description,
        first_half_sales, 
        second_half_sales,
        (first_half_sales - second_half_sales) AS sales_drop
    FROM time_period
    WHERE second_half_sales < first_half_sales 
    AND first_half_sales > 0;

-- Which products have the highest average selling price?
    CREATE OR REPLACE VIEW product.top_product_by_avg_price AS 
    SELECT 
    dp.description, 
    ROUND(SUM(fs.revenue) / NULLIF(SUM(fs.quantity), 0), 2) AS avg_selling_price
    FROM fact_sales AS fs
    INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
    GROUP BY dp.description;

-- What percentage of revenue comes from the top 10 products?
    CREATE OR REPLACE VIEW product.top_10_revenue_concentration AS 
    WITH product_revenue AS (
        SELECT dp.description, 
        SUM(fs.revenue) AS total_product_revenue
        FROM fact_sales AS fs
        INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
        GROUP BY dp.description
    ),
    product_ranking AS (
        SELECT
        total_product_revenue,
        ROW_NUMBER() OVER (ORDER BY total_product_revenue DESC) AS product_rank
        FROM product_revenue
    )
    SELECT 
    ROUND(SUM(CASE WHEN product_rank <= 10 THEN total_product_revenue ELSE 0 END),2) AS top_10_product_revenue,
    ROUND(SUM(total_product_revenue),2) AS grand_total_revenue,
    ROUND(100.0 * SUM(CASE WHEN product_rank <= 10 THEN total_product_revenue ELSE 0 END) / SUM(total_product_revenue),2) AS percentage_of_total_revenue
    FROM product_ranking;

-- Which products are frequently purchased together?
    CREATE OR REPLACE VIEW product.affinity_pairs AS 
    WITH normal_invoices AS (
        SELECT invoice_no
        FROM fact_sales
        GROUP BY invoice_no
        HAVING COUNT(DISTINCT stock_code) <= 100
    ),
    filtered_sales AS (
        SELECT 
        fs.invoice_no,
        fs.stock_code
        FROM fact_sales AS fs
        INNER JOIN normal_invoices AS ni ON fs.invoice_no = ni.invoice_no
    ),
    total_orders AS (
        SELECT COUNT(DISTINCT invoice_no) AS grand_total_invoices
        FROM normal_invoices
    )
    SELECT 
        dp1.description AS product_a, 
        dp2.description AS product_b, 
        COUNT(DISTINCT fs1.invoice_no) AS unique_combination,
        ROUND(100.0 * COUNT(DISTINCT fs1.invoice_no) 
        / t.grand_total_invoices, 3) AS support_percentage
    FROM filtered_sales AS fs1
    INNER JOIN filtered_sales AS fs2 ON fs1.invoice_no = fs2.invoice_no
    INNER JOIN dim_product AS dp1 ON fs1.stock_code = dp1.stock_code
    INNER JOIN dim_product AS dp2 ON fs2.stock_code = dp2.stock_code
    CROSS JOIN total_orders AS t
    WHERE fs1.stock_code < fs2.stock_code
    GROUP BY dp1.description, dp2.description, t.grand_total_invoices
    HAVING COUNT(DISTINCT fs1.invoice_no) >= 20;
