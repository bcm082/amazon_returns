import pandas as pd
import streamlit as st
import os
import matplotlib.pyplot as plt
import plotly.express as px
from streamlit_option_menu import option_menu
import search_products  # Import the search_products module
import top_sellers  # Import the top_sellers module

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

def load_all_returns_data():
    # Directories
    returns_dir_2023 = 'Data/Returns/2023/'
    returns_dir_2024 = 'Data/Returns/2024/'

    # List files
    returns_files_2023 = list_files(returns_dir_2023, '.tsv')
    returns_files_2024 = list_files(returns_dir_2024, '.tsv')

    # Load data
    data_frames = []
    for file in returns_files_2023:
        df = load_data(os.path.join(returns_dir_2023, file), delimiter='\t')
        data_frames.append(df)
    for file in returns_files_2024:
        df = load_data(os.path.join(returns_dir_2024, file), delimiter='\t')
        data_frames.append(df)

    return pd.concat(data_frames, ignore_index=True)

def create_returns_summary_table(data):
    try:
        # First try parsing with default format
        data['Return request date'] = pd.to_datetime(data['Return request date'], errors='coerce')
        
        # If we have any NaT (Not a Time) values, try common date formats
        if data['Return request date'].isna().any():
            # Try different date formats
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', 
                          '%m-%d-%Y', '%d-%m-%Y', '%Y.%m.%d', '%d.%m.%Y']
            
            for date_format in date_formats:
                # Try to parse dates that are still NaT
                mask = data['Return request date'].isna()
                data.loc[mask, 'Return request date'] = pd.to_datetime(
                    data.loc[mask, 'Return request date'],
                    format=date_format,
                    errors='coerce'
                )
        
        # Drop rows where we couldn't parse the date
        data = data.dropna(subset=['Return request date'])
        
        # Extract year and month
        data['Year'] = data['Return request date'].dt.year
        data['Month'] = data['Return request date'].dt.strftime('%b')

        # Group by year and month, summing the 'Return quantity'
        summary = data.groupby(['Year', 'Month'])['Return quantity'].sum().unstack(fill_value=0)

        # Reorder columns to have months in calendar order
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        summary = summary[month_order]

        # Format the year to avoid commas
        summary.index = summary.index.map(str)  # Convert index to string to avoid formatting issues

        return summary
        
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
        # Return an empty DataFrame with the correct structure if there's an error
        empty_summary = pd.DataFrame(columns=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        empty_summary.index.name = 'Year'
        return empty_summary

def load_returns_data_2024():
    returns_dir_2024 = 'Data/Returns/2024/'
    returns_files_2024 = list_files(returns_dir_2024, '.tsv')
    data_frames = [load_data(os.path.join(returns_dir_2024, file), delimiter='\t') for file in returns_files_2024]
    return pd.concat(data_frames, ignore_index=True)

def load_sales_data_2024():
    sales_dir_2024 = 'Data/Sales/2024/'
    sales_files_2024 = list_files(sales_dir_2024, '.txt')
    data_frames = [load_data(os.path.join(sales_dir_2024, file), delimiter='\t') for file in sales_files_2024]
    return pd.concat(data_frames, ignore_index=True)

def create_top_returns_table(returns_data, sales_data):
    # Extract relevant columns
    returns_data = returns_data[['ASIN', 'Return quantity', 'Return Reason']]
    sales_data = sales_data[['asin', 'sku', 'quantity']]

    # Aggregate data
    returns_agg = returns_data.groupby('ASIN').agg({
        'Return quantity': 'sum',
        'Return Reason': lambda x: x.value_counts().idxmax()  # Get the most common return reason
    }).reset_index()

    sales_agg = sales_data.groupby('asin').agg({'sku': 'first', 'quantity': 'sum'}).reset_index()

    # Merge datasets
    merged_data = pd.merge(returns_agg, sales_agg, left_on='ASIN', right_on='asin', how='inner')

    # Calculate percentage of returns
    merged_data['Percentage of Returns'] = (merged_data['Return quantity'] / merged_data['quantity']) * 100

    # Sort and select top 50
    top_returns = merged_data.sort_values(by='Return quantity', ascending=False).head(50)

    # Select relevant columns
    top_returns = top_returns[['ASIN', 'sku', 'Return quantity', 'quantity', 'Percentage of Returns', 'Return Reason']]
    top_returns.rename(columns={'quantity': 'Total Sold', 'Return Reason': 'Top Return Reason'}, inplace=True)

    return top_returns

def create_returns_reasons_table(returns_data):
    # Group by Return Reason and calculate total returns and percentage
    reasons_agg = returns_data.groupby('Return Reason').agg({
        'Return quantity': 'sum'
    }).reset_index()

    # Calculate total returns
    total_returns = reasons_agg['Return quantity'].sum()
    reasons_agg['Percentage'] = (reasons_agg['Return quantity'] / total_returns) * 100

    # Sort by Return Quantity
    reasons_agg = reasons_agg.sort_values(by='Return quantity', ascending=False)

    # Select relevant columns
    reasons_table = reasons_agg[['Return Reason', 'Return quantity', 'Percentage']]
    reasons_table.rename(columns={'Return quantity': 'Total returns'}, inplace=True)

    return reasons_table

# Initialize session state for page navigation
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

# Sidebar navigation using option_menu
with st.sidebar:
    selected = option_menu("Main Menu", ["Home", "Search", "Top Sellers"], 
                           icons=['house', 'search', 'graph-up'], menu_icon="cast", default_index=0)

# Page content based on navigation
if selected == 'Home':
    # Load all returns data
    returns_data = load_all_returns_data()

    # Create summary table
    returns_summary_table = create_returns_summary_table(returns_data)

    st.title("Returns Summary Table")

    # Plot line graph with Plotly
    st.subheader("Returns Over Time")
    fig = px.line(returns_summary_table.T, labels={'value': 'Return Quantity', 'index': 'Month'}, 
                  title='Returns Over Time', markers=True)
    fig.update_traces(line=dict(color='green'), selector=dict(name='2023'))
    fig.update_traces(line=dict(color='red'), selector=dict(name='2024'))
    st.plotly_chart(fig)

    # Display summary table
    st.write(returns_summary_table.style.format(precision=0, na_rep='0'))

    # Load data for top returns table
    returns_data_2024 = load_returns_data_2024()
    sales_data_2024 = load_sales_data_2024()

    # Create top returns table
    top_returns_table = create_top_returns_table(returns_data_2024, sales_data_2024)

    st.title("Top 50 Returned SKUs of 2024")

    # Reset index to hide it
    top_returns_table = top_returns_table.reset_index(drop=True)

    # Format the table
    formatted_table = top_returns_table.style.format({
        'Percentage of Returns': '{:.2f}%'
    })

    # Display the table
    st.dataframe(formatted_table, hide_index=True)

    # Create and display returns reasons table
    returns_reasons_table = create_returns_reasons_table(returns_data_2024)
    st.title("Returns Reasons Table")

    # Format the percentage column
    formatted_reasons_table = returns_reasons_table.style.format({
        'Percentage': '{:.2f}%'
    })

    st.dataframe(formatted_reasons_table, hide_index=True)

elif selected == 'Search':
    search_products.search_products_page()  # Call the function from search_products

elif selected == 'Top Sellers':
    top_sellers.top_sellers_page()  # Call the function from top_sellers