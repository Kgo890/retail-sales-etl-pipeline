-- how frequently do adjustments occur
    CREATE OR REPLACE VIEW adjustment.frequency AS
    SELECT 
    dd.year,
    dd.month,
    COUNT(*) AS adjustment_count
    FROM fact_adjustment AS fd
    INNER JOIN dim_date AS dd 
        ON fd.date_key = dd.date_key
    GROUP BY dd.year, dd.month;


-- what are the most adjustment description 
    CREATE OR REPLACE VIEW adjustment.by_description AS
    SELECT 
    dp.description,
    COUNT(*) AS adjustment_count
    FROM fact_adjustment AS fd
    INNER JOIN dim_product AS dp 
        ON fd.stock_code = dp.stock_code
    GROUP BY dp.description;

-- what Are adjustment volumes increasing or decreasing over time?
    CREATE OR REPLACE VIEW adjustment.trend AS
    WITH monthly_adjustments AS (
        SELECT 
            dd.year,
            dd.month,
            dd.month_name,
            COUNT(*) AS adjustment_count
        FROM fact_adjustment AS fd
        INNER JOIN dim_date AS dd 
            ON fd.date_key = dd.date_key
        GROUP BY dd.year, dd.month, dd.month_name
    ),
    adjustment_trends AS (
        SELECT
            year,
            month,
            month_name,
            adjustment_count,
            LAG(adjustment_count) OVER (
                ORDER BY year, month
            ) AS previous_month_adjustments
        FROM monthly_adjustments
    )
    SELECT
        year,
        month,
        adjustment_count,
        previous_month_adjustments,
        ROUND(
            100.0 * (adjustment_count - previous_month_adjustments)
            / NULLIF(previous_month_adjustments, 0),
            2
        ) AS mom_growth_percentage,
        month_name,
        (year * 100 + month) AS year_month_sort,
        LEFT(month_name, 3) || ' ' || year AS month_year_label
    FROM adjustment_trends;
