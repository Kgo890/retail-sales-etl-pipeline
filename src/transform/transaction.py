import pandas as pd
import numpy as np
from pathlib import Path

# load dataset
data = r"C:\Users\Kaden\retail_sales_etl_pipeline\data\raw\data.csv"
data_ids = r"C:\Users\Kaden\retail_sales_etl_pipeline\data\raw\data_ids.csv"

data_df = pd.read_csv(data)
data_ids_df = pd.read_csv(data_ids)

raw_transactions = pd.concat([data_ids_df,data_df], axis=1)



# fixing columns types
normalize_raw_transactions = raw_transactions.copy()
normalize_raw_transactions['InvoiceDate'] = pd.to_datetime(normalize_raw_transactions["InvoiceDate"], errors='coerce')
normalize_raw_transactions['CustomerID'] = normalize_raw_transactions['CustomerID'].astype('Int64') 


# adding transaction_type
conditions = [
    # account adjustment
    normalize_raw_transactions['UnitPrice'] < 0,

    # cancellation
    normalize_raw_transactions['InvoiceNo'].astype(str).str.startswith('C', na=False),

    # inventory adjustment
    (normalize_raw_transactions['Quantity'] < 0) & 
    (normalize_raw_transactions['UnitPrice']  == 0) & 
    (normalize_raw_transactions['CustomerID'].isna()),

    # zero-value transactions
    (normalize_raw_transactions['Quantity'] > 0) & 
    (normalize_raw_transactions['UnitPrice']  == 0)
]

conditions_categories = [
    'Account Adjustment',
    'Cancellation',
    'Inventory Adjustment',
    'Zero-Value Transaction'
]

normalize_raw_transactions['TransactionType'] = np.select(conditions,conditions_categories, default='Sale')


# Identify exact duplicate rows
normalize_raw_transactions["IsExactDuplicate"] = normalize_raw_transactions.duplicated(keep='first')

# dropping exact duplicate rows 
clean_df = normalize_raw_transactions[normalize_raw_transactions['IsExactDuplicate'] == False].copy()

# Identify potential duplicate transaction lines
clean_df["IsPotentialDuplicateLine"] = (
    clean_df.duplicated(
        subset=['InvoiceNo','StockCode','Quantity'], 
        keep = False
    )
)



# making tables to save
sale_fact = clean_df[clean_df['TransactionType'] == 'Sale'].copy()

cancellations = clean_df[clean_df['TransactionType'] == 'Cancellation'].copy()

adjustments = clean_df[clean_df['TransactionType'].isin(['Account Adjustment','Inventory Adjustment'])].copy()

non_sales = clean_df[clean_df['TransactionType'] == 'Zero-Value Transaction'].copy()

potential_duplicates = clean_df[clean_df['IsPotentialDuplicateLine'] == True].copy()


# adding revenue to the facts table
sale_fact['revenue'] = sale_fact['Quantity'] * sale_fact['UnitPrice']

cancellations['revenue'] = cancellations['Quantity'] * cancellations['UnitPrice']
cancellations['Quantity'] = abs(cancellations['Quantity'])

adjustments['revenue'] = adjustments['Quantity'] * adjustments['UnitPrice']

# adding issue_type and duplicate_group_count
potential_duplicates['issue_type'] = "Potential Duplicate"

potential_duplicates['duplicate_group_count'] = potential_duplicates.groupby(['InvoiceNo','StockCode','Quantity']).transform('size')

# moving rows with a StockCode with 'POST' or 'DOT' or 'B'(adjust bad debt) to non_sale or adustment 
stock_series = sale_fact['StockCode'].astype(str)
stock_series1 = cancellations['StockCode'].astype(str)

non_sale_mask = stock_series.isin(['POST', 'DOT', 'C2', 'PADS']) | stock_series.str.startswith('gift')
non_sale_mask1 = stock_series1.isin(['POST', 'DOT', 'C2', 'PADS']) | stock_series1.str.startswith('gift')

adjustment_mask = stock_series.isin(['B', 'M', 'm', 'BANK CHARGES', 'AMAZONFEE', 'S', 'D']) | stock_series.str.startswith('DCG')
adjustment_mask1 = stock_series1.isin(['B', 'M', 'm', 'BANK CHARGES', 'AMAZONFEE', 'S', 'D']) | stock_series1.str.startswith('DCG')


rows_to_move_non_sale = sale_fact[non_sale_mask].copy()
rows_to_move_adjust = sale_fact[adjustment_mask].copy()
rows_to_move_non_sale1 = cancellations[non_sale_mask1].copy()
rows_to_move_adjust1 = cancellations[adjustment_mask1].copy()

rows_to_move_non_sale['TransactionType'] = 'Administrative / Postage'
rows_to_move_non_sale1['TransactionType'] = 'Administrative / Postage'
rows_to_move_adjust['TransactionType'] = 'Financial Adjustment'
rows_to_move_adjust1['TransactionType'] = 'Financial Adjustment'

non_sales = pd.concat([non_sales, rows_to_move_non_sale, rows_to_move_non_sale1], ignore_index=True)
adjustments = pd.concat([adjustments, rows_to_move_adjust, rows_to_move_adjust1], ignore_index=True)

cancellations = cancellations[~(non_sale_mask1 | adjustment_mask1)]
sale_fact = sale_fact[~(non_sale_mask | adjustment_mask)]

# saving tables to output 
tables = {'fact_sales': sale_fact,
          'fact_cancellations': cancellations,
          'fact_adjustments': adjustments,
          'non_sales': non_sales,
          'data_quality_potential_duplicates': potential_duplicates
          }

base_path = Path(r"C:\Users\Kaden\retail_sales_etl_pipeline\data\processed")


for file_name, df in tables.items():
    output_path = base_path / f"{file_name}.csv"
    df.to_csv(output_path,index=False)
    print(f"The {file_name} table is being push to {output_path}")
    
