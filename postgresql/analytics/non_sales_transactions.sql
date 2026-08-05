-- what are the most common non-sale transaction types
    CREATE OR REPLACE VIEW non_sales.transaction_mix AS
    SELECT
    transaction_type,
    COUNT(*) AS transaction_count
    FROM fact_non_sale
    GROUP BY transaction_type;

-- how do non-sale transactions change over time
    CREATE OR REPLACE VIEW non_sales.transaction_trends AS
    SELECT 
    dd.year, 
    dd.month, 
    dd.month_name,
    fns.transaction_type,
    COUNT(*) AS volume,
    (dd.year * 100 + dd.month) AS year_month_sort,
    LEFT(dd.month_name, 3) || ' ' || dd.year AS month_year_label
    FROM fact_non_sale AS fns
    INNER JOIN dim_date AS dd ON fns.date_key = dd.date_key
    GROUP BY dd.year, dd.month, dd.month_name, fns.transaction_type;