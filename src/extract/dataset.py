from ucimlrepo import fetch_ucirepo 
import pandas as pd
from pathlib import Path

# fetch dataset 
online_retail = fetch_ucirepo(id=352) 
  
target_path = Path(r"C:\Users\Kaden\retail_sales_etl_pipeline\data\raw\data.csv")
target_path1 = Path(r"C:\Users\Kaden\retail_sales_etl_pipeline\data\raw\data_ids.csv")
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path1.parent.mkdir(parents=True, exist_ok=True)




print(online_retail.data.features)

online_retail.data.features.to_csv(target_path,index=False)
online_retail.data.ids.to_csv(target_path1,index=False)




