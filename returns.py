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
        # Set low_memory=False to avoid DtypeWarning
        return pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, delimiter=delimiter, encoding='ISO-8859-1', low_memory=False)

def list_files(directory, file_extension):
    try:
        return [f for f in os.listdir(directory) if f.endswith(file_extension)]
    except FileNotFoundError:
        return []

@st.cache_data
def load_all_returns_data():
    returns_dir = 'Data/Returns'
    returns_files = []
    
    # Get all return files recursively
    for root, _, files in os.walk(returns_dir):
        for file in files:
            if file.endswith('.tsv'):
                returns_files.append(os.path.join(root, file))
    
    # Load and combine all returns files
    data_frames = []
    for file in returns_files:
        df = load_data(file, delimiter='\t')
        # Debug: Output the raw data loaded
        st.write(f"Debug - Loaded data from {file}:")
        st.write(df.head())
        data_frames.append(df)
    
    # Combine all data frames
    if data_frames:
        return pd.concat(data_frames, ignore_index=True)
    return pd.DataFrame()

def create_returns_summary_table(data):
    try:
        # Create a copy of the data to avoid SettingWithCopyWarning
        df = data.copy()
        
        # Convert dates to datetime
        df['Return request date'] = pd.to_datetime(df['Return request date'], errors='coerce')
        df = df.dropna(subset=['Return request date'])
        
        # Create a new DataFrame with just the columns we need
        summary_data = pd.DataFrame({
            'Year': df['Return request date'].dt.year,
            'Month_Num': df['Return request date'].dt.month,
            'Return quantity': df['Return quantity']
        })
        
        # Create the summary by year and month
        summary = summary_data.groupby(['Year', 'Month_Num'])['Return quantity'].sum().reset_index()
        
        # Create a pivot table
        pivot_table = pd.pivot_table(
            summary,
            values='Return quantity',
            index='Year',
            columns='Month_Num',
            fill_value=0
        )
        
        # Rename columns to month names
        month_names = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }
        pivot_table = pivot_table.rename(columns=month_names)
        
        # Ensure all months are present
        for month in month_names.values():
            if month not in pivot_table.columns:
                pivot_table[month] = 0
        
        # Sort columns by month order
        pivot_table = pivot_table[list(month_names.values())]
        
        # Convert index to strings
        pivot_table.index = pivot_table.index.astype(str)
        
        return pivot_table
        
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
        empty_summary = pd.DataFrame(0, 
            index=['2023', '2024'],
            columns=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        )
        return empty_summary

@st.cache_data
def load_returns_data_2024():
    returns_dir = 'Data/Returns/2024'
    returns_files = list_files(returns_dir, '.tsv')
    
    data_frames = []
    for file in returns_files:
        df = load_data(os.path.join(returns_dir, file), delimiter='\t')
        # Debug: Output the raw data loaded
        st.write(f"Debug - Loaded data from {file}:")
        st.write(df.head())
        data_frames.append(df)
    
    if data_frames:
        return pd.concat(data_frames, ignore_index=True)
    return pd.DataFrame()

@st.cache_data
def load_sales_data_2024():
    sales_dir = 'Data/Sales/2024'
    sales_files = list_files(sales_dir, '.txt')
    
    data_frames = []
    for file in sales_files:
        df = load_data(os.path.join(sales_dir, file), delimiter='\t')
        # Debug: Output the raw data loaded
        st.write(f"Debug - Loaded data from {file}:")
        st.write(df.head())
        data_frames.append(df)
    
    if data_frames:
        return pd.concat(data_frames, ignore_index=True)
    return pd.DataFrame()

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

    # Debug: Output the summary table
    st.write("Debug - Returns Summary Table:")
    st.write(returns_summary_table)

    # Plot line graph with Plotly
    st.subheader("Returns Over Time")
    
    # Convert the data for plotting
    plot_df = returns_summary_table.reset_index()
    plot_df = pd.melt(plot_df, id_vars=['Year'], var_name='Month', value_name='Returns')
    
    # Debug: Output the plot data
    st.write("Debug - Plot Data:")
    st.write(plot_df)

    # Create the line graph
    fig = px.line(
        plot_df,
        x='Month',
        y='Returns',
        color='Year',
        title='Returns Over Time',
        markers=True
    )
    
    # Customize the graph
    fig.update_traces(line=dict(color='green'), selector=dict(name='2023'))
    fig.update_traces(line=dict(color='red'), selector=dict(name='2024'))
    
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Return Quantity",
        legend_title="Year",
        hovermode='x unified'
    )
    
    # Display the plot
    st.plotly_chart(fig, use_container_width=True)

    # Display monthly breakdown table
    st.subheader("Monthly Returns Breakdown")
    st.dataframe(
        returns_summary_table.style.format(precision=0, na_rep='0'),
        use_container_width=True
    )

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