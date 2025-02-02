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

@st.cache_data
def load_sales_data():
    file_path = os.path.join('Data/Sales', 'Sales_2024.csv')
    if not os.path.exists(file_path):
        return pd.DataFrame()
    
    # Load sales data
    df = load_data(file_path, delimiter=',')
    # Select only needed columns immediately to reduce memory usage
    df = df[['asin', 'sku', 'quantity']]
    
    # Pre-aggregate sales data
    sales_by_sku = df.groupby(['sku', 'asin'])['quantity'].sum().reset_index()
    sales_by_sku.columns = ['Merchant SKU', 'ASIN', 'Total Sold 2024']
    
    return sales_by_sku

@st.cache_data
def load_returns_data():
    file_path = os.path.join('Data/Returns', 'Returns_2024.csv')
    if not os.path.exists(file_path):
        return pd.DataFrame(), pd.DataFrame()
    
    # Load returns data
    df = load_data(file_path, delimiter=',')
    # Select only needed columns
    df = df[['ASIN', 'Merchant SKU', 'Return quantity', 'Return Reason']]
    
    # Pre-calculate returns by SKU
    returns_by_sku = df.groupby('Merchant SKU').agg({
        'Return quantity': 'sum',
        'Return Reason': lambda x: pd.Series.mode(x)[0] if not x.empty else "No Returns"
    }).reset_index()
    
    returns_by_sku.columns = ['Merchant SKU', 'Total Returns 2024', 'Top Return Reason']
    
    return returns_by_sku, df

@st.cache_data
def create_top_sellers_table():
    # Load pre-aggregated data
    sales_by_sku = load_sales_data()
    returns_by_sku, _ = load_returns_data()
    
    # Merge sales and returns data
    merged_data = pd.merge(sales_by_sku, returns_by_sku, on='Merchant SKU', how='left')
    
    # Fill missing values
    merged_data['Total Returns 2024'] = merged_data['Total Returns 2024'].fillna(0)
    merged_data['Top Return Reason'] = merged_data['Top Return Reason'].fillna("No Returns")
    
    # Calculate return rate
    merged_data['Return Rate'] = (merged_data['Total Returns 2024'] / merged_data['Total Sold 2024'] * 100)
    
    # Get top 500 sellers
    top_sellers = merged_data.nlargest(500, 'Total Sold 2024')
    
    # Format return rate
    top_sellers['Return Rate'] = top_sellers['Return Rate'].apply(lambda x: f'{x:.2f}%')
    
    # Optimize column order for display
    top_sellers = top_sellers[[
        'Merchant SKU', 'ASIN', 'Total Sold 2024', 'Total Returns 2024', 
        'Return Rate', 'Top Return Reason'
    ]]
    
    return top_sellers

def top_sellers_page():
    st.title("Top 500 Sellers of 2024")
    
    with st.spinner('Loading top sellers data...'):
        # Create and display the top sellers table
        top_sellers = create_top_sellers_table()
        
        # Add description
        st.write("This table shows the 500 most sold SKUs in 2024, along with their returns data and top return reasons.")
        
        # Display the table with improved formatting
        st.dataframe(
            top_sellers,
            hide_index=True,
            column_config={
                "Total Sold 2024": st.column_config.NumberColumn(format="%d"),
                "Total Returns 2024": st.column_config.NumberColumn(format="%d"),
                "Return Rate": st.column_config.TextColumn(width="small"),
                "Top Return Reason": st.column_config.TextColumn(width="medium")
            }
        )
