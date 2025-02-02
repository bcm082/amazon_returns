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
def load_sales_data(year):
    file_path = os.path.join('Data/Sales', f'Sales_{year}.csv')
    if not os.path.exists(file_path):
        return pd.DataFrame()
    
    # Load sales data
    df = load_data(file_path, delimiter=',')
    # Select only needed columns immediately to reduce memory usage
    df = df[['asin', 'sku', 'quantity']]
    
    return df

@st.cache_data
def load_returns_data(year):
    file_path = os.path.join('Data/Returns', f'Returns_{year}.csv')
    if not os.path.exists(file_path):
        return pd.DataFrame(), pd.DataFrame()
    
    # Load returns data
    df = load_data(file_path, delimiter=',')
    # Select only needed columns
    df = df[['ASIN', 'Merchant SKU', 'Return quantity', 'Return Reason']]
    
    return df

def top_sellers_page():
    st.title("Top 500 Sellers of 2024")

    # Load 2024 data
    sales_data = load_sales_data(2024)
    returns_data = load_returns_data(2024)

    # Group sales data by ASIN
    sales_summary = sales_data.groupby('asin').agg({
        'sku': lambda x: ', '.join(sorted(set(x))),  # List all unique SKUs
        'quantity': 'sum'  # Sum quantities
    }).reset_index()

    # Group returns data by ASIN
    returns_summary = returns_data.groupby('ASIN').agg({
        'Merchant SKU': lambda x: ', '.join(sorted(set(x))),  # List all unique SKUs
        'Return quantity': 'sum',  # Sum return quantities
        'Return Reason': lambda x: x.mode().iloc[0] if not x.empty else "No returns"  # Most common return reason
    }).reset_index()

    # Merge sales and returns data
    merged_data = pd.merge(
        sales_summary,
        returns_summary,
        left_on='asin',
        right_on='ASIN',
        how='left'
    )

    # Fill NaN values
    merged_data = merged_data.fillna({
        'Return quantity': 0,
        'Return Reason': 'No returns'
    })

    # Use sales SKUs if available, otherwise use returns SKUs
    merged_data['SKUs'] = merged_data.apply(
        lambda row: row['sku'] if pd.notna(row.get('sku')) else row.get('Merchant SKU', ''),
        axis=1
    )

    # Calculate return rate
    merged_data['Return Rate'] = (merged_data['Return quantity'] / merged_data['quantity'] * 100).round(2)

    # Sort by quantity sold (descending) and take top 500
    top_500 = merged_data.nlargest(500, 'quantity')

    # Create display DataFrame
    display_data = pd.DataFrame({
        'ASIN': top_500['asin'],
        'SKUs': top_500['SKUs'],
        'Units Sold': top_500['quantity'].astype(int),
        'Returns': top_500['Return quantity'].astype(int),
        'Return Rate': top_500['Return Rate'],
        'Top Return Reason': top_500['Return Reason']
    })

    # Format numbers with commas
    formatted_data = display_data.style.format({
        'Units Sold': lambda x: f"{int(x):,}",
        'Returns': lambda x: f"{int(x):,}",
        'Return Rate': '{:.2f}%'
    })

    # Display the table
    st.dataframe(formatted_data, hide_index=True)
