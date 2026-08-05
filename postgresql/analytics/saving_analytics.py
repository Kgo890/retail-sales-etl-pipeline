import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text
from src.load.database import engine

OUTPUT_DIR = PROJECT_ROOT / "data" / "analytics"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

queries = [
    ("total_revenue_sales.csv", text("""
        SELECT SUM(revenue) AS total_sales_revenue
        FROM fact_sales;
    """)),
    ("revenue_by_month.csv", text("""
        SELECT dd.month_name, SUM(fs.revenue) AS total_sales_revenue, dd.month
        FROM fact_sales AS fs
        INNER JOIN dim_date AS dd
        ON fs.date_key = dd.date_key
        GROUP BY dd.month, dd.month_name
        ORDER BY dd.month;
    """)),
    ("revenue_by_year_n_month.csv", text("""
        SELECT dd.year, dd.month_name, SUM(fs.revenue) AS total_sales_revenue, dd.month
        FROM fact_sales AS fs
        INNER JOIN dim_date AS dd
        ON fs.date_key = dd.date_key
        GROUP BY dd.year, dd.month, dd.month_name
        ORDER BY dd.year, dd.month;
    """)),
    ("revenue_trends.csv", text("""
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
            100.0 * (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY year, month))
            / NULLIF(LAG(monthly_revenue) OVER (ORDER BY year, month), 0),
            2
            ) AS mom_growth_pct,
            month,
            (year * 100 + month) AS year_month_sort,
            LEFT(month_name, 3) || ' ' || year AS month_year_label
        FROM months_revenue
        ORDER BY year, month;
    """)),
    ("monthly_sales_performance.csv", text("""
        SELECT
            dd.year,
            dd.month_name,
            SUM(fs.revenue) AS total_sales_revenue,
            COUNT(fs.invoice_no) AS number_of_transactions,
            SUM(fs.quantity) AS total_items_sold,
            dd.month
        FROM fact_sales as fs
        INNER JOIN dim_date as dd
        ON fs.date_key = dd.date_key
        GROUP BY dd.year, dd.month, dd.month_name
        ORDER BY dd.year, dd.month;
    """)),

    ("product_sales_summary.csv", text("""
        SELECT
            fs.stock_code,
            dp.description,
            SUM(fs.revenue) AS total_sales_revenue,
            SUM(fs.quantity) AS total_quantity_sold,
            COUNT(fs.invoice_no) AS total_number_transactions
        FROM fact_sales as fs
        LEFT JOIN dim_product as dp ON fs.stock_code = dp.stock_code
        GROUP BY fs.stock_code, dp.description;
    """)),
    ("top_product_by_quantity.csv", text("""
        SELECT
            fs.stock_code,
            dp.description,
            SUM(fs.quantity) AS total_quantity_sold
        FROM fact_sales as fs
        LEFT JOIN dim_product as dp ON fs.stock_code = dp.stock_code
        GROUP BY fs.stock_code, dp.description
        ORDER BY total_quantity_sold DESC;
    """)),
    ("top_product_by_transactions.csv", text("""
        SELECT
            fs.stock_code,
            dp.description,
            count(*) AS total_number_of_transactions
        FROM fact_sales as fs
        LEFT JOIN dim_product as dp ON fs.stock_code = dp.stock_code
        GROUP BY fs.stock_code, dp.description
        ORDER BY total_number_of_transactions DESC;
    """)),
    ("frequent_low_revenue_per_purchase.csv", text("""
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
        FROM product_stats
        ORDER BY purchase_frequency DESC, revenue_per_purchase ASC;
    """)),
    ("high_revenue_low_volume_filtered.csv", text("""
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
        AND total_revenue >= 2220.02
        ORDER BY total_revenue DESC;
    """)),
    ("high_volume_low_revenue_products.csv", text("""
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
        AND revenue_tier = 1
        ORDER BY total_volume DESC, total_revenue ASC;
    """)),
    ("high_revenue_low_volume_products.csv", text("""
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
        AND revenue_tier = 1
        ORDER BY total_revenue DESC, total_volume ASC;
    """)),
    ("product_consistency_trends.csv", text("""
        SELECT
        dp.description,
        COUNT(DISTINCT (dd.year || '-' || dd.month)) AS unique_months_active,
        SUM(fs.quantity) AS total_units_sold
        FROM fact_sales AS fs
        INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        GROUP BY dp.description
        ORDER BY unique_months_active DESC, total_units_sold DESC;
    """)),
    ("product_sales_decline.csv", text("""
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
        AND first_half_sales > 0
        ORDER BY sales_drop DESC;
    """)),
    ("top_product_by_avg_price.csv", text("""
        SELECT
        dp.description,
        ROUND(SUM(fs.revenue) / NULLIF(SUM(fs.quantity), 0), 2) AS avg_selling_price
        FROM fact_sales AS fs
        INNER JOIN dim_product AS dp ON fs.stock_code = dp.stock_code
        GROUP BY dp.description
        ORDER BY avg_selling_price DESC;
    """)),
    ("top_10_revenue_concentration.csv", text("""
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
        ROUND(SUM(CASE WHEN product_rank <= 10 THEN total_product_revenue ELSE 0 END), 2) AS top_10_product_revenue,
        ROUND(SUM(total_product_revenue), 2) AS grand_total_revenue,
        ROUND(100.0 * SUM(CASE WHEN product_rank <= 10 THEN total_product_revenue ELSE 0 END) / SUM(total_product_revenue), 2) AS percentage_of_total_revenue
        FROM product_ranking;
    """)),
    ("product_affinity_pairs.csv", text("""
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
        HAVING COUNT(DISTINCT fs1.invoice_no) >= 20
        ORDER BY unique_combination DESC;
    """)),

    ("adjustment_frequency.csv", text("""
        SELECT
        dd.year,
        dd.month,
        COUNT(*) AS adjustment_count
        FROM fact_adjustment AS fd
        INNER JOIN dim_date AS dd
            ON fd.date_key = dd.date_key
        GROUP BY dd.year, dd.month
        ORDER BY dd.year, dd.month;
    """)),
    ("top_description.csv", text("""
        SELECT
        dp.description,
        COUNT(*) AS adjustment_count
        FROM fact_adjustment AS fd
        INNER JOIN dim_product AS dp
        ON fd.stock_code = dp.stock_code
        GROUP BY dp.description
        ORDER BY adjustment_count DESC;
    """)),
    ("adjustment_trends.csv", text("""
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
        FROM adjustment_trends
        ORDER BY year, month;
    """)),

    ("non_sale_transaction_mix.csv", text("""
        SELECT
        transaction_type,
        COUNT(*) AS transaction_count
        FROM fact_non_sale
        GROUP BY transaction_type
        ORDER BY transaction_count DESC;
    """)),
    ("non_sale_transaction_trends.csv", text("""
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
        GROUP BY dd.year, dd.month, dd.month_name, fns.transaction_type
        ORDER BY dd.year ASC, dd.month ASC, volume DESC;
    """)),

    ("country_revenue.csv", text("""
        SELECT dc.country, SUM(fs.revenue) AS total_revenue
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        GROUP BY dc.country
        ORDER BY total_revenue DESC;
    """)),
    ("country_order_volumes.csv", text("""
        SELECT dc.country, COUNT(DISTINCT fs.invoice_no) AS order_volume
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        GROUP BY dc.country
        ORDER BY order_volume DESC;
    """)),
    ("country_high_aov.csv", text("""
        SELECT dc.country,
        ROUND(SUM(fs.revenue)/COUNT(DISTINCT fs.invoice_no), 2) AS average_order_value
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        GROUP BY dc.country
        HAVING COUNT(DISTINCT fs.invoice_no) >= 10
        ORDER BY average_order_value DESC;
    """)),
    ("country_high_volume_low_aov.csv", text("""
        SELECT dc.country,
        COUNT(DISTINCT fs.invoice_no) AS order_volume,
        ROUND(SUM(fs.revenue)/COUNT(DISTINCT fs.invoice_no), 2) AS average_order_value
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        GROUP BY dc.country
        HAVING COUNT(DISTINCT fs.invoice_no) > 50
        ORDER BY average_order_value ASC;
    """)),
    ("country_low_volume_high_aov.csv", text("""
        SELECT dc.country,
        COUNT(DISTINCT fs.invoice_no) AS order_volume,
        ROUND(SUM(fs.revenue)/COUNT(DISTINCT fs.invoice_no), 2) AS average_order_value
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc ON fs.country_key = dc.country_key
        GROUP BY dc.country
        HAVING COUNT(DISTINCT fs.invoice_no) BETWEEN 10 AND 50
        ORDER BY average_order_value DESC;
    """)),
    ("geographic_revenue_share.csv", text("""
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
        SELECT country, ROUND((pbc.total_revenue_per_country/t.total_revenue) * 100, 2) AS percentage
        FROM product_by_country AS pbc
        CROSS JOIN total_revenue AS t
        ORDER BY percentage DESC;
    """)),
    ("country_revenue_per_customer.csv", text("""
        SELECT dc1.country,
        SUM(fs.revenue) AS total_revenue,
        COUNT(DISTINCT fs.customer_id) AS number_of_customers,
        ROUND((SUM(fs.revenue)/COUNT(DISTINCT fs.customer_id)), 2) AS revenue_per_customer
        FROM fact_sales AS fs
        INNER JOIN dim_country AS dc1 ON fs.country_key = dc1.country_key
        GROUP BY dc1.country
        HAVING COUNT(DISTINCT fs.customer_id) > 10
        ORDER BY revenue_per_customer DESC;
    """)),
    ("geographic_growth_trends.csv", text("""
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
        GROUP BY dc.country, dd.year, dd.month, dd.month_name
        ),
        grab_revenue AS (
            SELECT
            country,
            year,
            month,
            month_name,
            current_revenue,
            LAG(current_revenue) OVER (PARTITION BY country ORDER BY year, month) AS previous_revenue
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
        GROUP BY country
        ORDER BY avg_monthly_growth_rate DESC;
    """)),

    ("customer_revenue_summary.csv", text("""
        SELECT dc.customer_id, SUM(fs.revenue) AS total_customer_revenue
        FROM fact_sales as fs
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        GROUP BY dc.customer_id
        ORDER BY total_customer_revenue DESC;
    """)),
    ("customer_order_counts.csv", text("""
        SELECT dc.customer_id, COUNT(DISTINCT(fs.invoice_no)) AS number_of_orders
        FROM fact_sales AS fs
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        GROUP BY dc.customer_id
        ORDER BY number_of_orders DESC;
    """)),
    ("customer_average_order_value.csv", text("""
        SELECT
        dc.customer_id,
        ROUND(SUM(fs.revenue)/COUNT(DISTINCT(fs.invoice_no)), 2) AS average_order_value
        FROM fact_sales AS fs
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        GROUP BY dc.customer_id
        ORDER BY average_order_value DESC;
    """)),
    ("customer_purchase_frequency.csv", text("""
        SELECT
        dc.customer_id,
        COUNT(DISTINCT fs.invoice_no) AS total_orders,
        COUNT(DISTINCT (dd.date_key / 100)) AS active_months,
        ROUND(
            COUNT(DISTINCT fs.invoice_no) * 1.0
            / COUNT(DISTINCT (dd.date_key/100)), 2
            ) AS monthly_purchase_frequency
        FROM fact_sales AS fs
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        GROUP BY dc.customer_id
        ORDER BY total_orders DESC;
    """)),
    ("customer_revenue_concentration.csv", text("""
        WITH customer_revenue AS (
            SELECT dc.customer_id, SUM(fs.revenue) AS total_customer_revenue
            FROM fact_sales AS fs
            INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
            GROUP BY dc.customer_id
        ),
        customer_deciles AS (
            SELECT
            total_customer_revenue,
            NTILE(10) OVER (ORDER BY total_customer_revenue DESC) AS decile
            FROM customer_revenue
        )
        SELECT
            ROUND(SUM(CASE WHEN decile = 1 THEN total_customer_revenue ELSE 0 END), 2) AS top_10_percent_revenue,
            ROUND(SUM(total_customer_revenue), 2) AS grand_total_revenue,
            ROUND(100.0 * SUM(CASE WHEN decile = 1 THEN total_customer_revenue ELSE 0 END) / SUM(total_customer_revenue), 2) AS percentage_of_total_revenue
        FROM customer_deciles;
    """)),
    ("customer_monthly_order_averages.csv", text("""
        SELECT dd.year,
        dd.month_name,
        COUNT(DISTINCT fs.invoice_no) AS total_orders,
        COUNT(DISTINCT dc.customer_id) AS active_customers,
        ROUND(
            COUNT(DISTINCT fs.invoice_no) * 1.0
            / COUNT(DISTINCT dc.customer_id),
            2) AS avg_order_per_customer
        FROM fact_sales AS fs
        INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
        INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
        GROUP BY dd.year, dd.month, dd.month_name
        ORDER BY dd.year, dd.month;
    """)),
    ("customer_rfm_segments.csv", text("""
        WITH metrics_per_customer AS (
            SELECT
            dc.customer_id,
            SUM(fs.revenue) AS total_revenue,
            COUNT(DISTINCT fs.invoice_no) AS total_orders,
            COUNT(DISTINCT (dd.date_key / 100)) AS active_months,
            ROUND(COUNT(DISTINCT fs.invoice_no) * 1.0/COUNT(DISTINCT (dd.date_key/ 100)), 2) AS purchase_frequency,
            ROUND(SUM(fs.revenue) * 1.0 / COUNT(DISTINCT fs.invoice_no), 2) AS average_order_value
            FROM fact_sales AS fs
            INNER JOIN dim_customer AS dc ON fs.customer_id = dc.customer_id
            INNER JOIN dim_date AS dd ON fs.date_key = dd.date_key
            GROUP BY dc.customer_id
        ),
        segment_metrics AS (
            SELECT
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_frequency) AS median_frequency,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY average_order_value) AS median_aov
            FROM metrics_per_customer
        )
        SELECT
        m.customer_id,
        m.purchase_frequency,
        m.average_order_value,
        CASE WHEN m.purchase_frequency > sm.median_frequency AND m.average_order_value > sm.median_aov
                THEN 'High Frequency and High AOV'
        WHEN m.purchase_frequency <= sm.median_frequency AND m.average_order_value > sm.median_aov
                THEN 'Low Frequency and High AOV'
        WHEN m.purchase_frequency > sm.median_frequency AND m.average_order_value <= sm.median_aov
                THEN 'High Frequency and Low AOV'
        ELSE 'Low Frequency and Low AOV'
        END AS customer_segment
        FROM metrics_per_customer AS m
        CROSS JOIN segment_metrics AS sm
        ORDER BY total_revenue DESC;
    """)),

    ("cancellation_products_by_orders.csv", text("""
        SELECT dp.description,
        COUNT(DISTINCT fc.invoice_no) AS cancelled_orders
        FROM fact_cancellations AS fc
        INNER JOIN dim_product AS dp ON fc.stock_code = dp.stock_code
        GROUP BY dp.description
        ORDER BY cancelled_orders DESC;
    """)),
    ("cancellation_global_rate.csv", text("""
        SELECT
        (SELECT COUNT(DISTINCT invoice_no) FROM fact_sales) AS total_sales_orders,
        (SELECT COUNT(DISTINCT invoice_no) FROM fact_cancellations) AS total_cancelled_orders,
        ROUND(
            ((SELECT COUNT(DISTINCT invoice_no) FROM fact_cancellations)::NUMERIC /
            ((SELECT COUNT(DISTINCT invoice_no) FROM fact_sales) + (SELECT COUNT(DISTINCT invoice_no) FROM fact_cancellations))) * 100,
            2
        ) AS cancellation_percentage;
    """)),
    ("cancellation_products_by_volume.csv", text("""
        SELECT dp.description, SUM(fc.quantity) AS cancelled_total
        FROM fact_cancellations AS fc
        LEFT JOIN dim_product AS dp ON fc.stock_code = dp.stock_code
        GROUP BY dp.description
        ORDER BY cancelled_total DESC;
    """)),
    ("cancellation_rates_by_country.csv", text("""
        WITH unique_sales AS (
        SELECT country_key, COUNT(DISTINCT invoice_no) AS total_sales
        FROM fact_sales
        GROUP BY country_key
        ),
        unique_cancellations AS (
            SELECT country_key, COUNT(DISTINCT invoice_no) AS total_cancels
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
        LEFT JOIN dim_country AS dc ON us.country_key = dc.country_key
        ORDER BY cancellation_rate DESC;
    """)),
    ("cancellation_rates_by_product.csv", text("""
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
            NULLIF(ps.total_sold + COALESCE(pc.total_cancelled, 0), 0)) * 100,
            2
        ) AS unit_cancellation_rate
        FROM product_sales AS ps
        LEFT JOIN product_cancellations AS pc ON ps.stock_code = pc.stock_code
        WHERE ps.total_sold > 50
        ORDER BY unit_cancellation_rate DESC;
    """)),
    ("cancellation_trends_over_time.csv", text("""
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
        / NULLIF(
            ms.sales_count + COALESCE(mc.cancels_count, 0),
            0
        ) * 100,
        2
        ) AS cancellation_rate,
        ms.month,
        (ms.year * 100 + ms.month) AS year_month_sort,
        LEFT(ms.month_name, 3) || ' ' || ms.year AS month_year_label
        FROM monthly_sales AS ms
        LEFT JOIN monthly_cancels AS mc ON ms.year = mc.year AND ms.month = mc.month
        ORDER BY ms.year, ms.month;
    """)),
    ("cancellation_high_revenue_risk_matrix.csv", text("""
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
        WHERE revenue_tier = 1
        ORDER BY cancellation_rate DESC;
    """)),

    ("data_quality_duplicate_count.csv", text("""
        SELECT COUNT(*) AS potential_duplicate_transactions
        FROM data_quality_potential_duplicates;
    """)),
    ("data_quality_duplicate_groups.csv", text("""
        SELECT COUNT(DISTINCT invoice_no) AS potential_duplicate_groups
        FROM data_quality_potential_duplicates;
    """)),
    ("data_quality_duplicate_percentage.csv", text("""
        WITH potential_duplicates AS (
        SELECT COUNT(*) AS duplicate_records
        FROM data_quality_potential_duplicates
        ),
        total_records AS (
            SELECT COUNT(*) AS total_records
            FROM fact_sales
        )
        SELECT
            tr.total_records,
            pd.duplicate_records,
            ROUND(
                (pd.duplicate_records * 100.0)
                / NULLIF(tr.total_records, 0), 2
            ) AS percentage_of_potential_duplicates
        FROM potential_duplicates AS pd
        CROSS JOIN total_records AS tr;
    """)),
    ("data_quality_issue_mix.csv", text("""
        SELECT issue_type,
        COUNT(*) AS number_of_issues
        FROM data_quality_potential_duplicates
        GROUP BY issue_type
        ORDER BY number_of_issues DESC;
    """)),
    ("data_quality_duplicate_cluster_sizes.csv", text("""
        SELECT
            duplicate_group_count,
            COUNT(*) AS number_of_rows
        FROM data_quality_potential_duplicates
        GROUP BY duplicate_group_count
        ORDER BY duplicate_group_count;
    """)),
]

names = [name for name, _ in queries]
dupes = {n for n in names if names.count(n) > 1}
if dupes:
    raise ValueError(f"Duplicate output filenames detected, fix before running: {dupes}")

succeeded, failed = [], []

with engine.connect() as connection:
    for filename, query in queries:
        output_path = OUTPUT_DIR / filename
        try:
            df = pd.read_sql_query(query, connection)
            df.to_csv(output_path, index=False)
            print(f"Successfully wrote: {output_path}")
            succeeded.append(filename)
        except Exception as e:
            print(f"FAILED: {filename} -> {e}")
            failed.append((filename, e))
            connection.rollback()

print(f"\nDone. {len(succeeded)} succeeded, {len(failed)} failed.")
if failed:
    print("Failed queries:")
    for name, err in failed:
        print(f"  - {name}: {err}")