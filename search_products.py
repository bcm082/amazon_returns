import streamlit as st
import pandas as pd
import os
import numpy as np

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
    if os.path.exists(file_path):
        df = load_data(file_path, delimiter=',')
        # Select only needed columns immediately to reduce memory usage
        df = df[['asin', 'sku', 'product-name', 'quantity']]
        
        # Convert strings to lowercase for case-insensitive search
        df['asin_lower'] = df['asin'].str.lower()
        df['sku_lower'] = df['sku'].str.lower()
        df['product_name_lower'] = df['product-name'].str.lower()
        
        return df
    return pd.DataFrame()

@st.cache_data
def load_returns_data(year):
    file_path = os.path.join('Data/Returns', f'Returns_{year}.csv')
    if os.path.exists(file_path):
        df = load_data(file_path, delimiter=',')
        # Select only needed columns immediately
        df = df[['ASIN', 'Merchant SKU', 'Return quantity', 'Return Reason']]
        return df
    return pd.DataFrame()

@st.cache_data
def process_returns_data(_returns_data, asin):
    """Process returns data for a specific ASIN with caching"""
    filtered_returns = _returns_data[_returns_data['ASIN'] == asin]
    return_quantity = filtered_returns['Return quantity'].sum()
    reasons = filtered_returns.groupby('Return Reason')['Return quantity'].sum()
    return return_quantity, reasons

def clean_sku_string(sku):
    """Remove FBA from SKU if present and return the clean version"""
    return sku.replace('-FBA-', '-')

def get_unique_skus(skus):
    """Get unique SKUs removing FBA versions when non-FBA version exists"""
    # Split SKUs into a list and clean them
    sku_list = [sku.strip() for sku in skus.split(',')]
    
    # Create a dictionary to store clean SKUs and their original versions
    clean_to_original = {}
    for sku in sku_list:
        clean = clean_sku_string(sku)
        # If we haven't seen this clean SKU before, or if this is a non-FBA version
        if clean not in clean_to_original or '-FBA-' not in sku:
            clean_to_original[clean] = sku
    
    # Return sorted unique SKUs
    return ', '.join(sorted(clean_to_original.keys()))

def search_products_page():
    st.title("Search Products")

    # Single search bar with unique key
    search_query = st.text_input("Search by ASIN or SKU", "", key="product_search")

    if search_query:
        # Load data with caching
        sales_data_2023 = load_sales_data(2023)
        sales_data_2024 = load_sales_data(2024)
        sales_data_2025 = load_sales_data(2025)
        returns_data_2023 = load_returns_data(2023)
        returns_data_2024 = load_returns_data(2024)
        returns_data_2025 = load_returns_data(2025)

        # Add year column to track data source
        sales_data_2023['year'] = 2023
        sales_data_2024['year'] = 2024
        sales_data_2025['year'] = 2025
        returns_data_2023['year'] = 2023
        returns_data_2024['year'] = 2024
        returns_data_2025['year'] = 2025

        # Combine data from all years
        sales_data = pd.concat([sales_data_2023, sales_data_2024, sales_data_2025])
        returns_data = pd.concat([returns_data_2023, returns_data_2024, returns_data_2025])

        # Convert search query to uppercase
        search_query_upper = search_query.upper()

        # First try ASIN exact match
        sales_filtered = sales_data[sales_data['asin'].str.upper() == search_query_upper]
        returns_filtered = returns_data[returns_data['ASIN'].str.upper() == search_query_upper]

        # If no ASIN match, try SKU partial match
        if sales_filtered.empty and returns_filtered.empty:
            # Find ASINs with matching SKUs in sales data
            matching_sales_asins = sales_data[
                sales_data['sku'].str.upper().str.contains(search_query_upper, na=False)
            ]['asin'].unique()

            # Find ASINs with matching SKUs in returns data
            matching_returns_asins = returns_data[
                returns_data['Merchant SKU'].str.upper().str.contains(search_query_upper, na=False)
            ]['ASIN'].unique()

            # Combine matching ASINs
            matching_asins = list(set(matching_sales_asins) | set(matching_returns_asins))

            # Get all data for matching ASINs
            if matching_asins:
                sales_filtered = sales_data[sales_data['asin'].isin(matching_asins)]
                returns_filtered = returns_data[returns_data['ASIN'].isin(matching_asins)]

        if not sales_filtered.empty or not returns_filtered.empty:
            # Group sales data by ASIN and year
            sales_summary = sales_filtered.groupby(['asin', 'year']).agg({
                'sku': lambda x: ', '.join(sorted(set(x))),  # List all unique SKUs
                'quantity': 'sum'  # Sum all quantities
            }).reset_index()

            # Group returns data by ASIN and year
            returns_summary = returns_filtered.groupby(['ASIN', 'year']).agg({
                'Merchant SKU': lambda x: ', '.join(sorted(set(x))),  # List all unique SKUs
                'Return quantity': 'sum',  # Sum all return quantities
                'Return Reason': lambda x: x.mode().iloc[0] if not x.empty else "No returns"  # Most common return reason
            }).reset_index()

            # Merge sales and returns data
            merged_data = pd.merge(
                sales_summary, 
                returns_summary, 
                left_on=['asin', 'year'], 
                right_on=['ASIN', 'year'], 
                how='outer'
            )

            # Clean up merged data
            merged_data = merged_data.fillna({
                'Return quantity': 0,
                'quantity': 0,
                'Return Reason': 'No returns'
            })

            # Use the sales SKUs if available, otherwise use returns SKUs
            merged_data['SKUs'] = merged_data.apply(
                lambda row: row['sku'] if pd.notna(row.get('sku')) else row.get('Merchant SKU', ''),
                axis=1
            )

            # Calculate return rate per year
            merged_data['Return Rate'] = (merged_data['Return quantity'] / merged_data['quantity'] * 100).round(2)

            # Create separate DataFrames for each year
            data_2023 = merged_data[merged_data['year'] == 2023].copy()
            data_2024 = merged_data[merged_data['year'] == 2024].copy()
            data_2025 = merged_data[merged_data['year'] == 2025].copy()

            # Format the display data for each year
            display_2023 = pd.DataFrame({
                'ASIN': data_2023['asin'],
                'SKUs': data_2023['SKUs'],
                'Units Sold': data_2023['quantity'].astype(int),
                'Returns': data_2023['Return quantity'].astype(int),
                'Return Rate': data_2023['Return Rate'],
                'Top Return Reason': data_2023['Return Reason']
            }) if not data_2023.empty else pd.DataFrame()

            display_2024 = pd.DataFrame({
                'ASIN': data_2024['asin'],
                'SKUs': data_2024['SKUs'],
                'Units Sold': data_2024['quantity'].astype(int),
                'Returns': data_2024['Return quantity'].astype(int),
                'Return Rate': data_2024['Return Rate'],
                'Top Return Reason': data_2024['Return Reason']
            }) if not data_2024.empty else pd.DataFrame()

            display_2025 = pd.DataFrame({
                'ASIN': data_2025['asin'],
                'SKUs': data_2025['SKUs'],
                'Units Sold': data_2025['quantity'].astype(int),
                'Returns': data_2025['Return quantity'].astype(int),
                'Return Rate': data_2025['Return Rate'],
                'Top Return Reason': data_2025['Return Reason']
            }) if not data_2025.empty else pd.DataFrame()

            # Show summary statistics first
            st.header("Summary Statistics")
            st.markdown("""<style>
            .summary-box {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 20px;
                margin: 10px 0;
                background-color: #f8f9fa;
            }
            </style>""", unsafe_allow_html=True)
            
            # Calculate totals for all years
            total_units_2023 = display_2023['Units Sold'].sum() if not display_2023.empty else 0
            total_returns_2023 = display_2023['Returns'].sum() if not display_2023.empty else 0
            total_units_2024 = display_2024['Units Sold'].sum() if not display_2024.empty else 0
            total_returns_2024 = display_2024['Returns'].sum() if not display_2024.empty else 0
            total_units_2025 = display_2025['Units Sold'].sum() if not display_2025.empty else 0
            total_returns_2025 = display_2025['Returns'].sum() if not display_2025.empty else 0
            
            # Calculate return rates
            return_rate_2023 = (total_returns_2023 / total_units_2023 * 100) if total_units_2023 > 0 else 0
            return_rate_2024 = (total_returns_2024 / total_units_2024 * 100) if total_units_2024 > 0 else 0
            return_rate_2025 = (total_returns_2025 / total_units_2025 * 100) if total_units_2025 > 0 else 0

            # Calculate total across all years
            total_units = total_units_2023 + total_units_2024 + total_units_2025
            total_returns = total_returns_2023 + total_returns_2024 + total_returns_2025
            total_return_rate = (total_returns / total_units * 100) if total_units > 0 else 0

            # Display overall summary
            st.markdown("<div class='summary-box'>", unsafe_allow_html=True)
            st.subheader("Overall Performance")
            overall_cols = st.columns(3)
            with overall_cols[0]:
                st.metric("Total Units Sold", f"{int(total_units):,}")
            with overall_cols[1]:
                st.metric("Total Returns", f"{int(total_returns):,}")
            with overall_cols[2]:
                st.metric("Overall Return Rate", f"{total_return_rate:.2f}%")
            st.markdown("</div>", unsafe_allow_html=True)

            # Display yearly metrics
            st.markdown("<div class='summary-box'>", unsafe_allow_html=True)
            st.subheader("Yearly Breakdown")
            
            # 2025
            st.markdown("#### 2025")
            year_2025_cols = st.columns(3)
            with year_2025_cols[0]:
                st.metric("Units Sold", f"{int(total_units_2025):,}", 
                         delta=f"{int(total_units_2025 - total_units_2024):,}" if total_units_2024 > 0 else None)
            with year_2025_cols[1]:
                st.metric("Returns", f"{int(total_returns_2025):,}",
                         delta=f"{int(total_returns_2025 - total_returns_2024):,}" if total_returns_2024 > 0 else None)
            with year_2025_cols[2]:
                st.metric("Return Rate", f"{return_rate_2025:.2f}%",
                         delta=f"{(return_rate_2025 - return_rate_2024):.2f}%" if return_rate_2024 > 0 else None)

            # 2024
            st.markdown("#### 2024")
            year_2024_cols = st.columns(3)
            with year_2024_cols[0]:
                st.metric("Units Sold", f"{int(total_units_2024):,}",
                         delta=f"{int(total_units_2024 - total_units_2023):,}" if total_units_2023 > 0 else None)
            with year_2024_cols[1]:
                st.metric("Returns", f"{int(total_returns_2024):,}",
                         delta=f"{int(total_returns_2024 - total_returns_2023):,}" if total_returns_2023 > 0 else None)
            with year_2024_cols[2]:
                st.metric("Return Rate", f"{return_rate_2024:.2f}%",
                         delta=f"{(return_rate_2024 - return_rate_2023):.2f}%" if return_rate_2023 > 0 else None)

            # 2023
            st.markdown("#### 2023")
            year_2023_cols = st.columns(3)
            with year_2023_cols[0]:
                st.metric("Units Sold", f"{int(total_units_2023):,}")
            with year_2023_cols[1]:
                st.metric("Returns", f"{int(total_returns_2023):,}")
            with year_2023_cols[2]:
                st.metric("Return Rate", f"{return_rate_2023:.2f}%")
            st.markdown("</div>", unsafe_allow_html=True)

            # Display 2025 results first
            if not display_2025.empty:
                st.subheader("2025 Results")
                formatted_2025 = display_2025.style.format({
                    'Units Sold': lambda x: f"{int(x):,}",
                    'Returns': lambda x: f"{int(x):,}",
                    'Return Rate': '{:.2f}%'
                })
                st.dataframe(formatted_2025, hide_index=True)

            # Display 2024 results
            if not display_2024.empty:
                st.subheader("2024 Results")
                formatted_2024 = display_2024.style.format({
                    'Units Sold': lambda x: f"{int(x):,}",
                    'Returns': lambda x: f"{int(x):,}",
                    'Return Rate': '{:.2f}%'
                })
                st.dataframe(formatted_2024, hide_index=True)

            # Then display 2023 results
            if not display_2023.empty:
                st.subheader("2023 Results")
                formatted_2023 = display_2023.style.format({
                    'Units Sold': lambda x: f"{int(x):,}",
                    'Returns': lambda x: f"{int(x):,}",
                    'Return Rate': '{:.2f}%'
                })
                st.dataframe(formatted_2023, hide_index=True)

        else:
            st.info("No products found matching your search criteria.")

search_products_page()
