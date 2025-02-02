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
    returns_files = ['Returns_2023.csv', 'Returns_2024.csv']
    
    # Load and combine all returns files
    data_frames = []
    for file in returns_files:
        file_path = os.path.join(returns_dir, file)
        if os.path.exists(file_path):
            df = load_data(file_path, delimiter=',')
            data_frames.append(df)
    
    # Combine all data frames
    if data_frames:
        return pd.concat(data_frames, ignore_index=True)
    return pd.DataFrame()

def create_returns_summary_table(data):
    try:
        # Create a copy of the data to avoid SettingWithCopyWarning
        df = data.copy()
        
        # Ensure that all required columns are present
        if 'Return request date' not in df.columns or 'Return quantity' not in df.columns:
            st.error("Missing required columns in the data.")
            return pd.DataFrame()

        # Convert dates to datetime
        try:
            df['Return request date'] = pd.to_datetime(df['Return request date'])
            df = df.dropna(subset=['Return request date'])
        except Exception as e:
            st.error(f"Error converting dates: {str(e)}")
            return pd.DataFrame()

        # Create a new DataFrame with just the columns we need
        summary_data = pd.DataFrame({
            'Year': df['Return request date'].dt.year,
            'Month': df['Return request date'].dt.month,
            'Return quantity': df['Return quantity']
        })

        # Group by Year and Month and sum the return quantities
        summary = summary_data.groupby(['Year', 'Month'])['Return quantity'].sum().reset_index()

        # Create a pivot table for returns
        pivot_table = pd.pivot_table(
            summary,
            values='Return quantity',
            index='Year',
            columns='Month',
            fill_value=0,
            aggfunc='sum'
        ).astype(int)  # Convert to integers

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

        # Load sales data for both years
        sales_data = []
        for year in pivot_table.index:
            file_path = os.path.join('Data/Sales', f'Sales_{year}.csv')
            if os.path.exists(file_path):
                year_sales = pd.read_csv(file_path)
                year_sales['purchase-date'] = pd.to_datetime(year_sales['purchase-date'])
                year_sales['year'] = year_sales['purchase-date'].dt.year
                sales_data.append(year_sales)

        if sales_data:
            # Combine sales data
            sales_df = pd.concat(sales_data)
            
            # Calculate yearly totals for both returns and sales
            yearly_returns = pivot_table.sum(axis=1)
            yearly_sales = sales_df.groupby('year')['quantity'].sum()
            
            # Add Total Units column
            pivot_table['Total Units'] = yearly_sales.astype(int)  # Convert to integers
            
            # Calculate and add return rate
            pivot_table['Return Rate'] = (yearly_returns / yearly_sales * 100).round(2)

        # Convert index to strings
        pivot_table.index = pivot_table.index.astype(str)

        # Create line graph
        st.subheader("Monthly Returns Trend")
        
        # Convert pivot table to format suitable for plotting
        plot_data = pivot_table.reset_index()
        plot_columns = list(month_names.values())  # Only use month columns for plotting
        plot_data = pd.melt(plot_data, 
                           id_vars=['Year'], 
                           value_vars=plot_columns,
                           var_name='Month',
                           value_name='Returns')
        
        # Create the line graph using plotly
        fig = px.line(
            plot_data,
            x='Month',
            y='Returns',
            color='Year',
            title='Returns by Month and Year',
            markers=True
        )

        # Customize the layout
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Returns",
            hovermode='x unified',
            xaxis=dict(
                tickmode='array',
                ticktext=list(month_names.values()),
                tickvals=list(month_names.values())
            ),
            legend_title="Year",
            showlegend=True
        )

        # Update line colors and styles
        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=8)
        )
        
        # Set specific colors for each year
        for trace in fig.data:
            if trace.name == "2023":
                trace.line.color = "rgb(0, 128, 0)"  # Green
            elif trace.name == "2024":
                trace.line.color = "rgb(220, 20, 60)"  # Crimson

        # Display the graph
        st.plotly_chart(fig, use_container_width=True)

        # Display the table with custom formatting
        st.subheader("Monthly Returns Breakdown")
        
        # Format all numeric columns except Return Rate
        numeric_cols = list(month_names.values()) + ['Total Units']
        
        # Create formatter dictionary for all columns
        formatters = {}
        for col in numeric_cols:
            formatters[col] = lambda x: f"{int(x):,}"
        formatters['Return Rate'] = lambda x: f"{x:.2f}%"
        
        # Apply formatting
        styled_table = pivot_table.style.format(formatters)
        
        # Display the table
        st.dataframe(styled_table, use_container_width=True)

        return pivot_table

    except Exception as e:
        st.error(f"Error creating summary table: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def load_returns_data_2024():
    file_path = os.path.join('Data/Returns', 'Returns_2024.csv')
    if os.path.exists(file_path):
        return load_data(file_path, delimiter=',')
    return pd.DataFrame()

@st.cache_data
def load_sales_data_2024():
    file_path = os.path.join('Data/Sales', 'Sales_2024.csv')
    if os.path.exists(file_path):
        return load_data(file_path, delimiter=',')
    return pd.DataFrame()

def create_top_returns_table(returns_data, sales_data):
    try:
        if returns_data.empty or sales_data.empty:
            return pd.DataFrame()

        # Group returns by ASIN
        returns_by_asin = returns_data.groupby('ASIN').agg({
            'Return quantity': 'sum',
            'Return Reason': lambda x: x.mode().iloc[0] if not x.empty else "No returns"
        }).reset_index()

        # Group sales by ASIN
        sales_by_asin = sales_data.groupby('asin')['quantity'].sum().reset_index()
        sales_by_asin.columns = ['ASIN', 'Total Sales']

        # Merge returns and sales data
        merged_data = pd.merge(returns_by_asin, sales_by_asin, on='ASIN', how='left')
        merged_data['Return Rate'] = (merged_data['Return quantity'] / merged_data['Total Sales'] * 100).round(2)
        
        # Sort by return quantity in descending order
        top_returns = merged_data.nlargest(10, 'Return quantity')
        
        return top_returns

    except Exception as e:
        st.error(f"Error creating top returns table: {str(e)}")
        return pd.DataFrame()

def create_returns_reasons_table(returns_data):
    try:
        if returns_data.empty:
            return pd.DataFrame()

        # Group by return reason and sum quantities
        reasons_summary = returns_data.groupby('Return Reason')['Return quantity'].sum().reset_index()
        reasons_summary = reasons_summary.sort_values('Return quantity', ascending=False)
        
        return reasons_summary

    except Exception as e:
        st.error(f"Error creating returns reasons table: {str(e)}")
        return pd.DataFrame()

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

    # Load data for top returns table
    returns_data_2024 = load_returns_data_2024()
    sales_data_2024 = load_sales_data_2024()

    # Create top returns table
    top_returns_table = create_top_returns_table(returns_data_2024, sales_data_2024)

    st.title("Top 10 Returned SKUs of 2024")

    # Reset index to hide it
    top_returns_table = top_returns_table.reset_index(drop=True)

    # Format the table
    formatted_table = top_returns_table.style.format({
        'Return Rate': '{:.2f}%'
    })

    # Display the table
    st.dataframe(formatted_table, hide_index=True)

    # Create and display returns reasons table
    returns_reasons_table = create_returns_reasons_table(returns_data_2024)
    st.title("Returns Reasons Table")

    st.dataframe(returns_reasons_table, hide_index=True)

elif selected == 'Search':
    search_products.search_products_page()  # Call the function from search_products

elif selected == 'Top Sellers':
    top_sellers.top_sellers_page()  # Call the function from top_sellers