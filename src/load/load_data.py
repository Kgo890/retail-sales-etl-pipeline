import os
import pandas as pd
from functools import partial
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from database import engine
import hashlib

DATA_DIR = "C:/Users/Kaden/retail_sales_etl_pipeline/data/processed"

DATA_FILES = {
     "sales": f"{DATA_DIR}/fact_sales.csv",
     "cancellations": f"{DATA_DIR}/fact_cancellations.csv",
     "adjustment": f"{DATA_DIR}/fact_adjustments.csv",
     "non_sales": f"{DATA_DIR}/non_sales.csv",
     "data_quality": f"{DATA_DIR}/data_quality_potential_duplicates.csv"
}

def add_row_hash(df, key_columns):
      df = df.copy()
      combined = df[key_columns].astype(str).agg('-'.join,axis=1)
      df['row_hash'] = combined.apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())
      return df


def load_processed_data():
     sales_df = pd.read_csv(DATA_FILES["sales"], low_memory= False)
     cancellations_df = pd.read_csv(DATA_FILES['cancellations'], low_memory= False)
     adjustment_df = pd.read_csv(DATA_FILES['adjustment'], low_memory= False)
     non_sales_df = pd.read_csv(DATA_FILES['non_sales'], low_memory=False)
     data_quality_df = pd.read_csv(DATA_FILES['data_quality'], low_memory=False)
     return (sales_df, cancellations_df,adjustment_df,non_sales_df,data_quality_df)

def clean_transaction_data(df):
     clean_df = df.copy()
     if 'StockCode' in clean_df.columns:
           clean_df['StockCode'] = clean_df['StockCode'].astype(str).str.strip()
     if 'Description' in clean_df.columns:
               clean_df['Description'] = clean_df['Description'].fillna('Unknown').astype(str).str.strip()
     if 'Country' in clean_df.columns:
               clean_df['Country'] = clean_df['Country'].fillna('Unknown').astype(str).str.strip()
     if 'InvoiceDate' in clean_df.columns:
            clean_df['InvoiceDate'] = pd.to_datetime(clean_df['InvoiceDate'])
     return clean_df
          
def build_dimensions(sales_df,cancellations_df, adjustment_df, non_sales_df):
     all_transactions = pd.concat([sales_df,cancellations_df,adjustment_df,non_sales_df], ignore_index=True)
     dim_product = (all_transactions[['StockCode', 'Description']]
                         .dropna(subset=['StockCode'])
                         .drop_duplicates(subset=['StockCode'])
                         .rename(columns={'StockCode': 'stock_code', 'Description': 'description'}))

     dim_customer = (all_transactions[['CustomerID']]
                .dropna()
                .drop_duplicates()
                .rename(columns={'CustomerID': "customer_id"}))

     dim_country = (all_transactions[['Country']]
               .dropna()
               .drop_duplicates()
               .rename(columns={'Country': 'country'}))

     unique_dates = pd.Series(all_transactions['InvoiceDate'].dt.normalize().unique())

     dim_date = pd.DataFrame({
     'date_key':unique_dates.dt.strftime('%Y%m%d').astype(int),
     'full_date': unique_dates.dt.date,
     'year': unique_dates.dt.year,
     'month': unique_dates.dt.month,
     'month_name': unique_dates.dt.strftime('%B'),
     'week': unique_dates.dt.isocalendar().week,
     'day': unique_dates.dt.day,
     'day_of_week': unique_dates.dt.dayofweek,
     'day_name': unique_dates.dt.strftime('%A')
     })

     return dim_country,dim_customer,dim_product,dim_date

def insert_on_conflict_do_nothing(table,conn,keys,data_iter,conflict_keys=None):
      data = [dict(zip(keys, row)) for row in data_iter]
      if not data:
            return 

      num_columns = len(keys)
      internal_batch_size = max(1,5000 // num_columns)

      if not conflict_keys:
        conflict_keys = [c.name for c in table.table.columns if c.primary_key]

    
      for i in range(0, len(data), internal_batch_size):
            sub_chunk = data[i:i + internal_batch_size]
        
            stmt = insert(table.table).values(sub_chunk)
            if conflict_keys:
                  stmt = stmt.on_conflict_do_nothing(index_elements=conflict_keys)
        
            conn.execute(stmt)

def load_dimensions(dim_country,dim_customer,dim_product,dim_date):
       dim_product.to_sql('dim_product', con=engine, if_exists='append', index=False, chunksize=5000,
                          method=partial(insert_on_conflict_do_nothing, conflict_keys=['stock_code']))
       dim_customer.to_sql('dim_customer', con=engine, if_exists='append', index=False, chunksize=5000,
                           method=partial(insert_on_conflict_do_nothing, conflict_keys=['customer_id']))
       dim_country.to_sql('dim_country', con=engine, if_exists='append', index=False, chunksize=5000,
                          method=partial(insert_on_conflict_do_nothing, conflict_keys=['country']))
       dim_date.to_sql('dim_date', con=engine, if_exists='append', index=False, chunksize=5000,
                       method=partial(insert_on_conflict_do_nothing, conflict_keys=['date_key']))
       print("Dimension tables are loaded")


def create_lookups():
     postgres_dim_country = pd.read_sql_table('dim_country',engine)
     postgres_dim_date = pd.read_sql_table('dim_date',engine)

     country_lookup = postgres_dim_country.set_index('country')['country_key']
     date_lookup = postgres_dim_date.set_index('full_date')['date_key']

     return country_lookup, date_lookup

def prepare_standard_fact(df, country_lookup, date_lookup):
       df = df.copy()
       df.rename(columns = {
          'InvoiceNo':'invoice_no',
          'StockCode':'stock_code',
          'Description': 'description',
          'Quantity':'quantity',
          'InvoiceDate':'invoice_date',
          'UnitPrice':'unit_price',
          'CustomerID':'customer_id',
          'revenue':'revenue'
       }, inplace=True)

       df['country_key'] = df['Country'].map(country_lookup)
       df['date_key'] = df['invoice_date'].dt.date.map(date_lookup)

       df = add_row_hash(df,['invoice_no', 'stock_code', 'description', 'quantity', 'invoice_date', 'unit_price'])

       fact_df = df[[
          'row_hash',
          'invoice_no',
          'stock_code',
          'quantity',
          'invoice_date',
          'unit_price',
          'customer_id',
          'country_key',
          'revenue',
          'date_key']]

       return fact_df


def prepare_non_sale_fact(df,country_lookup,date_lookup):
       df = df.copy()
       df.rename(columns = {
               'InvoiceNo':'invoice_no',
               'StockCode':'stock_code',
               'Description': 'description',
               'Quantity':'quantity',
               'InvoiceDate':'invoice_date',
               'UnitPrice':'unit_price',
               'CustomerID':'customer_id',
               'TransactionType': 'transaction_type'
          }, inplace=True)

       df['country_key'] = df['Country'].map(country_lookup)
       df['date_key'] = df['invoice_date'].dt.date.map(date_lookup)

       fact_df = df[[
          'invoice_no',
          'stock_code',
          'description',
          'quantity',
          'invoice_date',
          'unit_price',
          'customer_id',
          'country_key',
          'transaction_type',
          'date_key' 
          ]]

       return fact_df

def validate_fact_table(df,table_name):
       missing_country = df['country_key'].isna().sum()
       missing_date = df['date_key'].isna().sum()

       print(f"\n{table_name}")
       print("-" * 40)
       print(f"Rows: {len(df)}")
       print(f"Missing country keys: {missing_country}")
       print(f"Missing date keys: {missing_date}")

       if missing_country > 0:
          raise ValueError(f"{table_name} contains missing country keys.")

       if missing_date > 0:
          raise ValueError(f"{table_name} contains missing date keys.")

def load_fact_table(df,table_name,conflict_keys=None):
      df.to_sql(
            table_name, con=engine, if_exists='append',index=False, chunksize=5000,
            method=lambda t, c, k, d: insert_on_conflict_do_nothing(t, c, k, d, conflict_keys=conflict_keys)
            )
      print(f"Loading {len(df)} rows into {table_name}")


def prepare_data_quality(df):
      df = df.copy()
      df.rename(columns = {
          'InvoiceNo':'invoice_no',
          'StockCode':'stock_code',
          'Quantity':'quantity',
          'Description': 'description',
          'InvoiceDate':'invoice_date',
          'UnitPrice':'unit_price',
          'CustomerID':'customer_id',
          'Country': 'country',
          'TransactionType': 'transaction_type'
      }, inplace=True)

      data_quality_df = df[[
          'invoice_no',
          'stock_code',
          'quantity',
          'description',
          'invoice_date',
          'unit_price',
          'customer_id',
          'country',
          'transaction_type',
          'issue_type',
          'duplicate_group_count'
       ]]
      return data_quality_df

def main():
      print("Loading Data...")

      sales_df,cancellations_df,adjustment_df,non_sales_df,data_quality_df = load_processed_data()

      print("Processed CSV files loaded")

      sales_df = clean_transaction_data(sales_df)
      cancellations_df = clean_transaction_data(cancellations_df)
      adjustment_df = clean_transaction_data(adjustment_df)
      non_sales_df = clean_transaction_data(non_sales_df)
      data_quality_df = clean_transaction_data(data_quality_df)

      print("Transaction data cleaned")

      dim_country,dim_customer,dim_product,dim_date = build_dimensions(sales_df,cancellations_df,adjustment_df, non_sales_df)

      load_dimensions(dim_country,dim_customer,dim_product,dim_date)

      country_lookup, date_lookup = create_lookups()

      fact_sales = prepare_standard_fact(sales_df,country_lookup,date_lookup)
      fact_cancellations = prepare_standard_fact(cancellations_df,country_lookup,date_lookup)
      fact_adjustments = prepare_standard_fact(adjustment_df,country_lookup,date_lookup)
      fact_non_sales = prepare_non_sale_fact(non_sales_df,country_lookup,date_lookup)
      fact_data_quality = prepare_data_quality(data_quality_df)

      validate_fact_table(fact_sales,"fact_sales")
      validate_fact_table(fact_cancellations,'fact_cancellations')
      validate_fact_table(fact_adjustments,'fact_adjustment')
      validate_fact_table(fact_non_sales,'fact_non_sales')


      print("\nLoading fact_tables")
      with engine.begin() as conn:
                  conn.execute(text("TRUNCATE TABLE data_quality_potential_duplicates;"))

      load_fact_table(fact_sales,"fact_sales",conflict_keys=['row_hash'])
      load_fact_table(fact_cancellations,"fact_cancellations",conflict_keys=['row_hash'])
      load_fact_table(fact_adjustments,"fact_adjustment",conflict_keys=['row_hash'])
      load_fact_table(fact_non_sales,"fact_non_sale",conflict_keys=['row_hash'])

      fact_data_quality.to_sql(
            'data_quality_potential_duplicates', con=engine,
            if_exists='append', index=False,chunksize=5000
      )

      print("\nData load is complete")

if __name__ == "__main__":
     print("\n-- Starting ETL pipeline ingestion ---")
     try:
          main()
     except Exception as e:
          print("\n!!! PIPELINE CRASHED WITH AN ERROR !!!")
          import traceback
          traceback.print_exc()
