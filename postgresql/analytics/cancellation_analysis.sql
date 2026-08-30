-- what percentage of orders are cancellations 
CREATE OR REPLACE VIEW cancellation.global_rate AS 
    WITH sales_count AS (
        SELECT 
        COUNT(DISTINCT invoice_no) AS total_sales_orders
        FROM fact_sales
    ),
    cancellation_counts AS (
        SELECT 
        COUNT(DISTINCT invoice_no) AS total_cancelled_orders
        FROM fact_cancellations
    ), 
    total_counts AS (
        SELECT 
        s.total_sales_orders, 
        c.total_cancelled_orders,
        (s.total_sales_orders + c.total_cancelled_orders) AS total_order_count
        FROM sales_count AS s
        CROSS JOIN cancellation_counts AS c
    )

    SELECT 
        total_sales_orders,
        total_cancelled_orders, 
        ROUND(100.0 * (total_cancelled_orders::NUMERIC / NULLIF(total_order_count, 0 )), 2) AS cancellation_percentage
    FROM total_counts; 


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
