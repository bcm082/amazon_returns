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

def load_sales_data(year):
    sales_dir = f'Data/Sales/{year}/'
    sales_files = list_files(sales_dir, '.txt')
    data_frames = [load_data(os.path.join(sales_dir, file), delimiter='\t') for file in sales_files]
    return pd.concat(data_frames, ignore_index=True)

def load_returns_data(year):
    returns_dir = f'Data/Returns/{year}/'
    returns_files = list_files(returns_dir, '.tsv')
    data_frames = [load_data(os.path.join(returns_dir, file), delimiter='\t') for file in returns_files]
    return pd.concat(data_frames, ignore_index=True)

def search_products_page():
    st.title("Search Products")

    # Create a search bar
    search_query = st.text_input("Search for a product (ASIN, SKU, or Product Name)", "")

    if search_query:
        # Load data
        sales_data_2023 = load_sales_data(2023)
        sales_data_2024 = load_sales_data(2024)
        returns_data_2023 = load_returns_data(2023)
        returns_data_2024 = load_returns_data(2024)

        # Search logic
        search_results_2023 = sales_data_2023[
            (sales_data_2023['asin'].str.contains(search_query, case=False, na=False)) |
            (sales_data_2023['sku'].str.contains(search_query, case=False, na=False)) |
            (sales_data_2023['product-name'].str.contains(search_query, case=False, na=False))
        ]

        search_results_2024 = sales_data_2024[
            (sales_data_2024['asin'].str.contains(search_query, case=False, na=False)) |
            (sales_data_2024['sku'].str.contains(search_query, case=False, na=False)) |
            (sales_data_2024['product-name'].str.contains(search_query, case=False, na=False))
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

            # Prepare yearly data
            yearly_data = []
            for _, row in unique_products.iterrows():
                asin = row['asin']
                sku = row['sku']
                
                # 2023 data
                returns_2023 = returns_data_2023[returns_data_2023['ASIN'] == asin]['Return quantity'].sum()
                sales_2023 = search_results_2023[search_results_2023['asin'] == asin]['quantity'].sum()
                return_rate_2023 = (returns_2023 / sales_2023 * 100) if sales_2023 > 0 else 0
                
                # 2024 data
                returns_2024 = returns_data_2024[returns_data_2024['ASIN'] == asin]['Return quantity'].sum()
                sales_2024 = search_results_2024[search_results_2024['asin'] == asin]['quantity'].sum()
                return_rate_2024 = (returns_2024 / sales_2024 * 100) if sales_2024 > 0 else 0
                
                yearly_data.extend([
                    {'SKU': sku, 'Year': '2023', 'Returns': returns_2023, 'Sales': sales_2023, 'Return Rate': f'{return_rate_2023:.2f}%'},
                    {'SKU': sku, 'Year': '2024', 'Returns': returns_2024, 'Sales': sales_2024, 'Return Rate': f'{return_rate_2024:.2f}%'}
                ])

            st.subheader("Yearly Data")
            yearly_data_table = pd.DataFrame(yearly_data)
            st.dataframe(yearly_data_table, hide_index=True)

            # Display return reasons
            st.subheader("Return Reasons")
            all_reasons = []
            for _, row in unique_products.iterrows():
                asin = row['asin']
                sku = row['sku']
                
                reasons_2023 = returns_data_2023[returns_data_2023['ASIN'] == asin].groupby('Return Reason')['Return quantity'].sum()
                reasons_2024 = returns_data_2024[returns_data_2024['ASIN'] == asin].groupby('Return Reason')['Return quantity'].sum()
                
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
