import streamlit as st
import pandas as pd
import os

@st.cache_data
def load_data(file_path, delimiter):
    try:
        return pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8')
    except UnicodeDecodeError:
        return pd.read_csv(file_path, delimiter=delimiter, encoding='ISO-8859-1')

def list_files(directory, file_extension):
    try:
        return [f for f in os.listdir(directory) if f.endswith(file_extension)]
    except FileNotFoundError:
        return []

def load_sales_data():
    sales_dir = 'Data/Sales/2024/'
    sales_files = list_files(sales_dir, '.txt')
    
    # Load and combine all sales files
    data_frames = []
    for file in sales_files:
        df = load_data(os.path.join(sales_dir, file), delimiter='\t')
        # Select only needed columns
        df = df[['asin', 'sku', 'quantity']]
        data_frames.append(df)
    
    return pd.concat(data_frames, ignore_index=True)

def load_returns_data():
    returns_dir = 'Data/Returns/2024/'
    returns_files = list_files(returns_dir, '.tsv')
    
    # Load and combine all returns files
    data_frames = []
    for file in returns_files:
        df = load_data(os.path.join(returns_dir, file), delimiter='\t')
        # Select only needed columns
        df = df[['ASIN', 'Merchant SKU', 'Return quantity', 'Return Reason']]
        data_frames.append(df)
    
    return pd.concat(data_frames, ignore_index=True)

def get_top_return_reason(returns_data, sku):
    # Filter returns for the specific SKU
    sku_returns = returns_data[returns_data['Merchant SKU'] == sku]
    if sku_returns.empty:
        return "No Returns"
    
    # Group by return reason and get the most common one
    top_reason = sku_returns.groupby('Return Reason')['Return quantity'].sum().sort_values(ascending=False)
    if top_reason.empty:
        return "No Returns"
    return top_reason.index[0]

def create_top_sellers_table():
    # Load data
    sales_data = load_sales_data()
    returns_data = load_returns_data()
    
    # Calculate total sales by SKU
    sales_by_sku = sales_data.groupby(['sku', 'asin'])['quantity'].sum().reset_index()
    sales_by_sku.columns = ['SKU', 'ASIN', 'Total Sold 2024']
    
    # Calculate total returns by SKU
    returns_by_sku = returns_data.groupby('Merchant SKU')['Return quantity'].sum().reset_index()
    returns_by_sku.columns = ['SKU', 'Total Returns 2024']
    
    # Merge sales and returns data
    merged_data = pd.merge(sales_by_sku, returns_by_sku, on='SKU', how='left')
    merged_data['Total Returns 2024'] = merged_data['Total Returns 2024'].fillna(0)
    
    # Calculate return rate
    merged_data['Return Rate'] = (merged_data['Total Returns 2024'] / merged_data['Total Sold 2024'] * 100)
    
    # Get top return reason for each SKU
    merged_data['Top Return Reason'] = merged_data['SKU'].apply(
        lambda x: get_top_return_reason(returns_data, x)
    )
    
    # Sort by total sold and get top 500
    top_sellers = merged_data.nlargest(500, 'Total Sold 2024')
    
    # Format return rate
    top_sellers['Return Rate'] = top_sellers['Return Rate'].apply(lambda x: f'{x:.2f}%')
    
    return top_sellers

def top_sellers_page():
    st.title("Top 500 Sellers of 2024")
    
    # Create and display the top sellers table
    top_sellers = create_top_sellers_table()
    
    # Add description
    st.write("This table shows the 500 most sold SKUs in 2024, along with their returns data and top return reasons.")
    
    # Display the table
    st.dataframe(top_sellers, hide_index=True)
