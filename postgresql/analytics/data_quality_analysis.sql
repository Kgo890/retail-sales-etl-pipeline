-- what percentage of the dataset contains potential duplicates
    CREATE OR REPLACE VIEW data_quality.duplicate_percentage AS
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
            / NULLIF(tr.total_records, 0),2
        ) AS percentage_of_potential_duplicates
    FROM potential_duplicates AS pd
    CROSS JOIN total_records AS tr;
