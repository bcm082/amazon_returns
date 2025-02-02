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

def search_products_page():
    st.title("Search Products")

    # Create a search bar
    search_query = st.text_input("Search for a product (ASIN, SKU, or Product Name)", "")

    if search_query:
        # Convert search query to lowercase once
        search_query_lower = search_query.lower()
        
        # Load data with caching
        sales_data_2023 = load_sales_data(2023)
        sales_data_2024 = load_sales_data(2024)
        returns_data_2023 = load_returns_data(2023)
        returns_data_2024 = load_returns_data(2024)

        # Optimized search logic using pre-computed lowercase columns
        search_results_2023 = sales_data_2023[
            (sales_data_2023['asin_lower'].str.contains(search_query_lower, na=False)) |
            (sales_data_2023['sku_lower'].str.contains(search_query_lower, na=False)) |
            (sales_data_2023['product_name_lower'].str.contains(search_query_lower, na=False))
        ]

        search_results_2024 = sales_data_2024[
            (sales_data_2024['asin_lower'].str.contains(search_query_lower, na=False)) |
            (sales_data_2024['sku_lower'].str.contains(search_query_lower, na=False)) |
            (sales_data_2024['product_name_lower'].str.contains(search_query_lower, na=False))
        ]

        # Calculate metrics
        if not search_results_2023.empty or not search_results_2024.empty:
            # Get unique products
            unique_products_2023 = search_results_2023[['asin', 'sku']].drop_duplicates()
            unique_products_2024 = search_results_2024[['asin', 'sku']].drop_duplicates()
            unique_products = pd.concat([unique_products_2023, unique_products_2024]).drop_duplicates()

            # Display first section
            st.subheader("Product Identification")
            id_table = pd.DataFrame({
                'ASIN': unique_products['asin'],
                'Amazon Link': unique_products['asin'].apply(lambda x: f'https://www.amazon.com/dp/{x}'),
                'SKU': unique_products['sku']
            })
            st.dataframe(id_table, hide_index=True)

            # Prepare yearly data more efficiently
            yearly_data = []
            for _, row in unique_products.iterrows():
                asin = row['asin']
                sku = row['sku']
                
                # Process returns data with caching
                returns_2023, reasons_2023 = process_returns_data(returns_data_2023, asin)
                returns_2024, reasons_2024 = process_returns_data(returns_data_2024, asin)
                
                # Process sales data
                sales_2023 = search_results_2023[search_results_2023['asin'] == asin]['quantity'].sum()
                sales_2024 = search_results_2024[search_results_2024['asin'] == asin]['quantity'].sum()
                
                return_rate_2023 = (returns_2023 / sales_2023 * 100) if sales_2023 > 0 else 0
                return_rate_2024 = (returns_2024 / sales_2024 * 100) if sales_2024 > 0 else 0
                
                yearly_data.extend([
                    {'SKU': sku, 'Year': '2023', 'Returns': returns_2023, 'Sales': sales_2023, 'Return Rate': f'{return_rate_2023:.2f}%'},
                    {'SKU': sku, 'Year': '2024', 'Returns': returns_2024, 'Sales': sales_2024, 'Return Rate': f'{return_rate_2024:.2f}%'}
                ])

            st.subheader("Yearly Data")
            yearly_data_table = pd.DataFrame(yearly_data)
            st.dataframe(yearly_data_table, hide_index=True)

            # Display return reasons more efficiently
            all_reasons = []
            for _, row in unique_products.iterrows():
                asin = row['asin']
                sku = row['sku']
                
                _, reasons_2023 = process_returns_data(returns_data_2023, asin)
                _, reasons_2024 = process_returns_data(returns_data_2024, asin)
                
                # Combine reasons for both years
                all_reasons_product = pd.DataFrame({
                    'SKU': sku,
                    'Return Reason': reasons_2023.index.union(reasons_2024.index),
                })
                all_reasons_product['Return quantity 2023 Count'] = all_reasons_product['Return Reason'].map(reasons_2023).fillna(0)
                all_reasons_product['Return quantity 2024 Count'] = all_reasons_product['Return Reason'].map(reasons_2024).fillna(0)
                all_reasons.append(all_reasons_product)
            
            if all_reasons:
                reasons_table = pd.concat(all_reasons, ignore_index=True)
                reasons_table_sorted = reasons_table.sort_values(by=['SKU', 'Return quantity 2024 Count'], ascending=[True, False])
                st.dataframe(reasons_table_sorted, hide_index=True)
        else:
            st.write("No results found for the search query.")
    else:
        st.write("Enter a product name, ASIN, or SKU to search.")
