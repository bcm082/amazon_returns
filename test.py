import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
import os

# Set page config
st.set_page_config(
    page_title="Year-over-Year Sales Analysis",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
    }
    .st-emotion-cache-1y4p8pa {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

def load_data():
    """Load the main CSV data file and inventory data."""
    main_file_path = "Data/yoy-2023-2024.csv"
    inventory_file_path = "Data/inventory.csv"
    
    if not os.path.exists(main_file_path):
        return None
        
    # Load main data
    df = pd.read_csv(main_file_path)
    
    # Load and merge inventory data if available
    if os.path.exists(inventory_file_path):
        inventory_df = pd.read_csv(inventory_file_path)
        # Merge with main dataframe
        df = df.merge(inventory_df[['SKU', 'Inventory']], 
                     on='SKU', 
                     how='left')
        # Replace '--' with 0 and handle NaN values
        df['Inventory'] = df['Inventory'].replace('--', '0')
        df['Inventory'] = pd.to_numeric(df['Inventory'], errors='coerce').fillna(0).astype(int)
        # Rename Inventory column to Current Inventory
        df = df.rename(columns={'Inventory': 'Current Inventory'})
    else:
        # Add empty Current Inventory column if inventory file doesn't exist
        df['Current Inventory'] = 0
        
    return df

def apply_numeric_filter(df, column, operator, value):
    """Apply numeric filter based on operator and value."""
    if operator == '>':
        return df[df[column] > value]
    elif operator == '>=':
        return df[df[column] >= value]
    elif operator == '<':
        return df[df[column] < value]
    elif operator == '<=':
        return df[df[column] <= value]
    elif operator == '==':
        return df[df[column] == value]
    return df

def search_products(df, search_term):
    """Search products by name or SKU."""
    if not search_term:
        return df
    
    # Trim whitespace and convert search term to lowercase for case-insensitive search
    search_term = search_term.strip().lower()
    mask = (df['Name'].str.lower().str.contains(search_term, na=False) |
            df['SKU'].str.lower().str.contains(search_term, na=False))
    return df[mask]

def main():
    # Title and description
    st.title("📊 Year-over-Year Sales Analysis")
    st.markdown("---")

    # Load data
    df = load_data()
    
    if df is None:
        st.error("Data file not found. Please ensure 'yoy-2023-2024.csv' exists in the Data folder.")
        return

    # Search functionality
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search by Product Name or SKU", "")
    
    with col2:
        st.write("")
        show_filters = st.checkbox("Show Advanced Filters", value=False)
    
    # Filter data based on search
    filtered_df = search_products(df, search_term)
    
    if show_filters:
        st.markdown("### Advanced Filters")
        
        # Get numeric columns (excluding 'Year' and 'SKU')
        numeric_columns = filtered_df.select_dtypes(include=['int64', 'float64']).columns
        numeric_columns = [col for col in numeric_columns if col not in ['Year']]
        
        # Initialize session state for number of filters if not exists
        if 'num_filters' not in st.session_state:
            st.session_state.num_filters = 1
        
        # Add filter button
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button('Add Filter') and st.session_state.num_filters < 3:
                st.session_state.num_filters += 1
        
        # Display filters
        for i in range(st.session_state.num_filters):
            cols = st.columns([2, 1, 1])
            
            with cols[0]:
                # Set default value for first column to 'Current Inventory', others remain as 'None'
                default_value = 'Current Inventory' if i == 0 else 'None'
                column = st.selectbox(f'Column {i+1}', ['None'] + list(numeric_columns), key=f'col_{i}', index=(['None'] + list(numeric_columns)).index(default_value))
            
            if column != 'None':
                with cols[1]:
                    # Set default operator to '>=' for first column, no default for others
                    default_operator_index = 1 if i == 0 else 0  # 1 is the index of '>='
                    operator = st.selectbox('Operator', ['>', '>=', '<', '<=', '=='], key=f'op_{i}', index=default_operator_index)
                with cols[2]:
                    value = st.number_input('Value', value=0, key=f'val_{i}')
                
                if column in filtered_df.columns:
                    filtered_df = apply_numeric_filter(filtered_df, column, operator, value)
        
        # Remove filter button (only show if more than 1 filter)
        if st.session_state.num_filters > 1:
            if st.button('Remove Last Filter'):
                st.session_state.num_filters -= 1
    
    # Display results count
    st.markdown(f"### Found {len(filtered_df)} products")
    
    # Display data
    if not filtered_df.empty:
        # Convert Year column to string to avoid scientific notation
        filtered_df['Year'] = filtered_df['Year'].astype(str)
        
        # Display the data in a clean table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
        )
        
        # Show detailed analysis for selected product
        if len(filtered_df) == 1:
            product = filtered_df.iloc[0]
            st.markdown("### Monthly Sales Analysis")
            
            # Get monthly columns
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            # Create monthly sales data for chart
            monthly_data = product[months]
            
            # Display line chart
            st.line_chart(monthly_data)
    else:
        st.info("No products found matching your search criteria.")

if __name__ == "__main__":
    main()
