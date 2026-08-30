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
