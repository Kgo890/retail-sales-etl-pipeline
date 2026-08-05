CREATE TABLE IF NOT EXISTS dim_product (
    stock_code TEXT PRIMARY KEY,
    description TEXT
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS dim_country (
    country_key INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    country TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE,
    year INTEGER,
    month INTEGER,
    month_name TEXT,
    week INTEGER,
    day INTEGER,
    day_of_week INTEGER,
    day_name TEXT
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE,
    invoice_no TEXT,
    stock_code TEXT, 
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id INTEGER,
    country_key INTEGER,
    revenue NUMERIC(12,2),
    date_key INTEGER,

    CONSTRAINT fk_sales_product FOREIGN KEY (stock_code) REFERENCES dim_product (stock_code),
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_id) REFERENCES dim_customer (customer_id),
    CONSTRAINT fk_sales_country FOREIGN KEY (country_key) REFERENCES dim_country (country_key),
    CONSTRAINT fk_sales_date FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_cancellations (
    cancel_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE,
    invoice_no TEXT,
    stock_code TEXT, 
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id INTEGER,
    country_key INTEGER,
    revenue NUMERIC(12,2),
    date_key INTEGER,

    CONSTRAINT fk_cancellations_product FOREIGN KEY (stock_code) REFERENCES dim_product (stock_code),
    CONSTRAINT fk_cancellations_customer FOREIGN KEY (customer_id) REFERENCES dim_customer (customer_id),
    CONSTRAINT fk_cancellations_country FOREIGN KEY (country_key) REFERENCES dim_country (country_key),
    CONSTRAINT fk_cancellations_date FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_adjustment (
    adjustment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE,
    invoice_no TEXT,
    stock_code TEXT, 
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id INTEGER,
    country_key INTEGER,
    revenue NUMERIC(12,2),
    date_key INTEGER,

    CONSTRAINT fk_adjustment_product FOREIGN KEY (stock_code) REFERENCES dim_product (stock_code),
    CONSTRAINT fk_adjustment_customer FOREIGN KEY (customer_id) REFERENCES dim_customer (customer_id),
    CONSTRAINT fk_adjustment_country FOREIGN KEY (country_key) REFERENCES dim_country (country_key),
    CONSTRAINT fk_adjustment_date FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS data_quality_potential_duplicates (
    quality_issue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_no TEXT,
    stock_code TEXT, 
    quantity INTEGER,
    description TEXT,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id INTEGER,
    country TEXT,
    transaction_type TEXT,
    issue_type TEXT,
    duplicate_group_count INTEGER
);

CREATE TABLE IF NOT EXISTS fact_non_sale (
    non_sale_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
	row_hash VARCHAR(32) UNIQUE,
    invoice_no TEXT,
    stock_code TEXT,
    description TEXT,
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id INTEGER,
    country_key INTEGER,
    transaction_type TEXT,
    date_key INTEGER,

    CONSTRAINT fk_non_sale_product FOREIGN KEY (stock_code) REFERENCES dim_product (stock_code),
    CONSTRAINT fk_non_sale_customer FOREIGN KEY (customer_id) REFERENCES dim_customer (customer_id),
    CONSTRAINT fk_non_sale_country FOREIGN KEY (country_key) REFERENCES dim_country (country_key),
    CONSTRAINT fk_non_sale_date FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);


CREATE SCHEMA IF NOT EXISTS adjustment;
CREATE SCHEMA IF NOT EXISTS cancellation;
CREATE SCHEMA IF NOT EXISTS customer;
CREATE SCHEMA IF NOT EXISTS data_quality;
CREATE SCHEMA IF NOT EXISTS geographic;
CREATE SCHEMA IF NOT EXISTS non_sales;
CREATE SCHEMA IF NOT EXISTS product;
CREATE SCHEMA IF NOT EXISTS sales;
