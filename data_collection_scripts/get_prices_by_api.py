from data_collection_scripts.utils.indian_api import get_or_load_data



endpoint = "historical_data"
stock_name = "TCS"
period = "1m"
filter = "price"
stats = "yoy_results"


get_or_load_data(endpoint, stock_name, period=period, filter=filter, stats=stats)