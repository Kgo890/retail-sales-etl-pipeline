-- how many potential duplicate transactions exist
    CREATE OR REPLACE VIEW data_quality.duplicate_count AS
    SELECT COUNT(*) AS potential_duplicate_transactions
    FROM data_quality_potential_duplicates;

-- how many potential duplicate groups exists
    CREATE OR REPLACE VIEW data_quality.duplicate_groups AS 
    SELECT COUNT(DISTINCT invoice_no) AS potential_duplicate_groups
    FROM data_quality_potential_duplicates;

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

-- what are the most common data_quality issues
    CREATE OR REPLACE VIEW data_quality.issue_mix AS 
    SELECT issue_type, 
    COUNT(*) AS number_of_issues
    FROM data_quality_potential_duplicates 
    GROUP BY issue_type;

 -- how large are the duplicate clusters (are most duplicates simple pairs or larger groups?)
    CREATE OR REPLACE VIEW data_quality.duplicate_cluster_sizes AS
    SELECT 
        duplicate_group_count,
        COUNT(*) AS number_of_rows
    FROM data_quality_potential_duplicates
    GROUP BY duplicate_group_count
    ORDER BY duplicate_group_count;