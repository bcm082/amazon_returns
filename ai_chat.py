import pandas as pd
import streamlit as st
import os
import time
import re
from pandasai.smart_dataframe import SmartDataframe
from pandasai.llm import OpenAI

# Environment variables should already be loaded in the conda environment

# Function to extract DataFrame-like text into a pandas DataFrame for Streamlit rendering
def extract_dataframe_from_text(text):
    # Define common column names to look for
    common_columns = ['sku', 'quantity', 'year', 'purchase', 'purchase-date', 'asin', 'return']
    
    # Check if text contains any data-like patterns
    has_data_pattern = False
    
    # Check for DataFrame-like patterns
    if any(col in text.lower() for col in common_columns):
        has_data_pattern = True
    elif re.search(r'\d+\s+\d+', text):  # Numbers separated by whitespace
        has_data_pattern = True
    elif '...' in text or '  ' in text:  # DataFrame ellipsis or multiple spaces
        has_data_pattern = True
    
    if has_data_pattern:
        try:
            # Extract lines and clean up
            lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
            if len(lines) < 2:
                return None, text
            
            # Try different approaches to identify column headers
            
            # Approach 1: Look for lines with common column names
            header_line = None
            for i, line in enumerate(lines):
                if any(col in line.lower() for col in common_columns):
                    header_line = line
                    data_start = i + 1
                    break
            
            # Approach 2: If no header found, look for patterns like "column1 column2"
            if not header_line:
                # The first line might be the header if it doesn't start with a number
                if not re.match(r'^\d', lines[0]):
                    header_line = lines[0]
                    data_start = 1
                else:
                    # Try to infer columns from the data
                    for col in common_columns:
                        if col in text.lower():
                            # If we find a column name anywhere in the text, use common column names
                            header_line = "index " + " ".join(common_columns)
                            data_start = 0
                            break
                    
                    # If still no header, create a generic one based on the number of columns in the first line
                    if not header_line:
                        # Count columns in the first data line by splitting on whitespace
                        values = [v for v in re.split(r'\s{2,}|\.{3}|\s+', lines[0]) if v.strip()]
                        if values and len(values) > 1:
                            # First value might be an index
                            if values[0].isdigit():
                                header_line = "index " + " ".join([f"column{i}" for i in range(len(values)-1)])
                            else:
                                header_line = " ".join([f"column{i}" for i in range(len(values))])
                            data_start = 0
                        else:
                            return None, text
            
            # Extract column names from the header line
            columns = [col.strip() for col in re.split(r'\s{2,}|\.{3}|\s+', header_line) if col.strip()]
            
            # If still no columns, use generic ones
            if not columns or len(columns) < 2:
                columns = ['Item', 'Value']
            
            # Process data rows
            data_rows = []
            for i, line in enumerate(lines):
                # Skip header line and summary lines
                if i < data_start or '[' in line and ']' in line or 'rows' in line:
                    continue
                    
                # Skip header-like lines or empty lines
                if not line.strip() or all(col.lower() in line.lower() for col in columns if isinstance(col, str)):
                    continue
                    
                # Split the line by multiple spaces, ellipsis, or any whitespace
                values = [val.strip() for val in re.split(r'\s{2,}|\.{3}|\s+', line) if val.strip()]
                
                # Handle different data row formats
                if values:
                    # Case 1: We have exactly the right number of columns
                    if len(values) == len(columns):
                        data_rows.append(values)
                    # Case 2: First value is an index, skip it
                    elif len(values) == len(columns) + 1 and values[0].isdigit():
                        data_rows.append(values[1:])
                    # Case 3: We have more values than columns, take the first len(columns)
                    elif len(values) > len(columns):
                        data_rows.append(values[:len(columns)])
                    # Case 4: We have fewer values than columns but at least 2 values
                    elif len(values) >= 2:
                        # Pad with empty strings
                        data_rows.append(values + [''] * (len(columns) - len(values)))
            
            # If we successfully parsed at least one data row, create a DataFrame
            if data_rows and len(columns) > 0:
                # Create a pandas DataFrame
                df = pd.DataFrame(data_rows, columns=columns)
                
                # Try to convert numeric columns
                for col in df.columns:
                    try:
                        # If the column contains only numbers, convert to numeric
                        if df[col].str.isnumeric().all():
                            df[col] = pd.to_numeric(df[col])
                    except:
                        pass
                
                # Determine the title for the table
                title = ""
                
                # Check for specific column combinations to determine table type
                cols_lower = [col.lower() if isinstance(col, str) else str(col).lower() for col in columns]
                
                # SKU-related tables
                if any(col in cols_lower for col in ['sku', 'asin']):
                    if 'quantity' in cols_lower:
                        # Check if we need to add a year context
                        if any('2023' in str(line) for line in lines) and any('2024' in str(line) for line in lines):
                            title = "Comparison of Products Between Years"
                        else:
                            title = "Top Products by Quantity"
                    else:
                        title = "Product Information"
                
                # Year-related tables
                elif any(col in cols_lower for col in ['year', 'purchase-date', 'purchase']):
                    if 'quantity' in cols_lower:
                        title = "Sales by Year"
                    else:
                        title = "Year Analysis"
                        
                # Return-related tables
                elif any(col in cols_lower for col in ['return']):
                    title = "Return Analysis"
                    
                # Generic table title if we couldn't determine a specific type
                if not title:
                    title = "Data Analysis Results"
                
                return df, title
            
        except Exception as e:
            # If parsing fails, return None
            pass
            
    return None, text

def ai_chat_page():
    st.title("AI Chat Assistant")
    st.write("Ask questions about your Amazon returns and sales data")
    
    # Add explanation about the data
    with st.expander("About the data"):
        st.markdown("""
        ### Data Sources
        
        This AI assistant can answer questions about two main datasets:
        
        **Returns Data**:
        - Contains information about product returns from 2023-2025
        - Includes fields like: ASIN, Merchant SKU, Return quantity, Return Reason, etc.
        - Use for questions about return rates, return reasons, and product return patterns
        
        **Sales Data**:
        - Contains information about product sales from 2023-2025
        - Includes fields like: ASIN, quantity, purchase-date, etc.
        - Use for questions about sales volume, revenue, and product performance
        
        You can ask questions that combine both datasets, such as "What products have high sales but also high return rates?"
        """)
    
    # Initialize session state variables if they don't exist
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
        st.session_state.data_dict = None
        st.session_state.llm = None
        
    if 'response_cache' not in st.session_state:
        st.session_state.response_cache = {}
    
    # Function to load and combine all data
    @st.cache_data
    def load_all_data():
        try:
            # Load Returns data
            returns_dir = 'Data/Returns'
            returns_files = ['Returns_2023.csv', 'Returns_2024.csv', 'Returns_2025.csv']
            
            returns_dfs = []
            for file in returns_files:
                file_path = os.path.join(returns_dir, file)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path, low_memory=False)
                    # The CSV already has a 'Return request date' column
                    # Convert date to datetime and extract year for easier filtering
                    if 'Return request date' in df.columns:
                        df['Return request date'] = pd.to_datetime(df['Return request date'], format='%m/%d/%y', errors='coerce')
                        df['Year'] = df['Return request date'].dt.year
                    returns_dfs.append(df)
            
            # Load Sales data
            sales_dir = 'Data/Sales'
            sales_files = ['Sales_2023.csv', 'Sales_2024.csv', 'Sales_2025.csv']
            
            sales_dfs = []
            for file in sales_files:
                file_path = os.path.join(sales_dir, file)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path, low_memory=False)
                    # The CSV already has a 'purchase-date' column
                    # Convert date to datetime and extract year for easier filtering
                    if 'purchase-date' in df.columns:
                        df['purchase-date'] = pd.to_datetime(df['purchase-date'], format='%m/%d/%y', errors='coerce')
                        df['Year'] = df['purchase-date'].dt.year
                    sales_dfs.append(df)
            
            # Create dictionaries to hold the dataframes
            data_dict = {}
            
            # Add returns dataframes to dictionary
            if returns_dfs:
                combined_returns = pd.concat(returns_dfs, ignore_index=True)
                data_dict['returns'] = combined_returns
            
            # Add sales dataframes to dictionary
            if sales_dfs:
                combined_sales = pd.concat(sales_dfs, ignore_index=True)
                data_dict['sales'] = combined_sales
            
            return data_dict
            
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return None
    
    # Load data if not already loaded
    if not st.session_state.data_loaded:
        with st.spinner("Loading data and initializing AI... This may take a moment."):
            data_dict = load_all_data()
            if data_dict:
                st.session_state.data_dict = data_dict
                
                # Initialize OpenAI LLM
                try:
                    llm = OpenAI(api_token=os.environ.get("OPENAI_API_KEY"))
                    st.session_state.llm = llm
                    st.session_state.data_loaded = True
                    st.success("Data loaded and AI initialized successfully!")
                        
                except Exception as e:
                    st.error(f"Error initializing AI: {str(e)}")
            else:
                st.error("Failed to load data.")
    
    # Add custom CSS for chat styling
    st.markdown("""
    <style>
        .ai-message {
            background-color: #f8f9fa;
            color: #333333;  /* Dark gray text for better contrast */
            border-radius: 8px;
            padding: 12px 16px;
            margin: 10px 0;
            border-left: 4px solid #4a6fa5;
            font-size: 1.05em;
            line-height: 1.5;
        }
        .user-message {
            margin: 10px 0;
            padding: 8px 0;
            font-weight: 500;
        }
        .ai-message table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        .ai-message th {
            background-color: #4a6fa5;
            color: white;
            padding: 8px;
            text-align: left;
        }
        .ai-message td {
            padding: 8px;
            border: 1px solid #ddd;
        }
        .ai-message tr:nth-child(even) {
            background-color: #f2f2f2;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display chat interface
    if st.session_state.data_loaded:
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for i, (role, message) in enumerate(st.session_state.chat_history):
                if role == "user":
                    st.markdown(f'<div class="user-message">👤 <strong>You:</strong> {message}</div>', unsafe_allow_html=True)
                else:
                    # Wrap AI response in a styled div
                    st.markdown(f'<div class="ai-message">🤖 <strong>AI:</strong> {message}</div>', unsafe_allow_html=True)
                
                # Add a subtle separator between messages
                if i < len(st.session_state.chat_history) - 1:
                    st.markdown("<hr style='margin: 15px 0; border: 0; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)
        
        # Create a form for the chat input to handle Enter key submission
        with st.form(key='chat_form'):
            # Use a unique key for the text input that changes on each submission
            form_key = f"user_input_{len(st.session_state.chat_history)}"
            user_question = st.text_input(
                "Ask a question about your Amazon returns and sales data:",
                key=form_key
            )
            submitted = st.form_submit_button("Ask")
        
        # Process the user's question when the form is submitted
        if submitted and user_question:
            # This will clear the input field by using a new key on next render
            pass
            
            # Add user question to chat history
            st.session_state.chat_history.append(("user", user_question))
            
            # Check if the question is in the cache
            cache_key = user_question.strip().lower()
            
            if cache_key in st.session_state.response_cache:
                final_response = st.session_state.response_cache[cache_key]
                st.session_state.chat_history.append(("ai", final_response))
                st.rerun()
            
            # Process the question with PandasAI
            try:
                with st.spinner("Analyzing data and generating response..."):
                    start_time = time.time()
                    
                    # Determine which dataset(s) to query based on the question
                    sales_terms = ['sale', 'sales', 'sold', 'revenue', 'purchase', 'best selling', 'top selling', 'most sold', 'revenue', 'best seller', 'top seller', 'bestseller']
                    returns_terms = ['return', 'returns', 'refund', 'refunds', 'reason', 'most returned']
                    
                    # Special case for "best selling" questions - these should ONLY use sales data
                    best_selling_terms = ['best selling', 'top selling', 'most sold', 'best seller', 'top seller', 'bestseller']
                    is_best_selling_question = any(term in user_question.lower() for term in best_selling_terms)
                    
                    # Check if this is a comparison question between years
                    comparison_terms = ['compare', 'comparison', 'versus', 'vs', 'difference', 'differences', 'between']
                    is_comparison_question = any(term in user_question.lower() for term in comparison_terms)
                    
                    # Extract years mentioned in the question
                    years_mentioned = []
                    for year in ['2023', '2024', '2025']:
                        if year in user_question:
                            years_mentioned.append(int(year))
                    
                    # Check if the question specifically mentions sales or returns
                    question_lower = user_question.lower()
                    use_sales = any(term in question_lower for term in sales_terms)
                    use_returns = any(term in question_lower for term in returns_terms)
                    
                    # Determine which datasets to query
                    datasets_to_query = []
                    
                    # Special case for best-selling questions - ONLY use sales data
                    if is_best_selling_question:
                        if 'sales' in st.session_state.data_dict:
                            datasets_to_query.append('sales')
                    # If question is clearly about sales, only use sales data
                    elif use_sales and not use_returns:
                        if 'sales' in st.session_state.data_dict:
                            datasets_to_query.append('sales')
                    # If question is clearly about returns, only use returns data
                    elif use_returns and not use_sales:
                        if 'returns' in st.session_state.data_dict:
                            datasets_to_query.append('returns')
                    # If question mentions both or is ambiguous, use both datasets
                    else:
                        if 'sales' in st.session_state.data_dict:
                            datasets_to_query.append('sales')
                        if 'returns' in st.session_state.data_dict:
                            datasets_to_query.append('returns')
                    
                    # Generate responses for each relevant dataset
                    responses = []
                    
                    # Process each relevant dataset
                    for dataset in datasets_to_query:
                        try:
                            # Add detailed context about the dataset to the question
                            if dataset == 'returns':
                                context = (
                                    "This data contains information about product returns including ASIN, Merchant SKU, Return quantity, and Return Reason. "
                                    "IMPORTANT: This is RETURNS data, not sales data. 'Return quantity' means the number of items returned by customers, not items sold. "
                                    "Do not use this data to answer questions about sales volume, revenue, or best-selling products."
                                )
                            else:  # sales
                                context = (
                                    "This data contains information about product sales including ASIN, SKU, quantity, and purchase date. "
                                    "This is SALES data showing products purchased by customers. The 'quantity' column represents the number of items sold. "
                                    "Use this data for questions about sales volume, revenue, or best-selling products."
                                )
                                
                            enhanced_question = f"{context} Based on this {dataset} data, {user_question}"
                            
                            # Create a SmartDataframe for this dataset
                            df = SmartDataframe(
                                st.session_state.data_dict[dataset], 
                                config={
                                    "llm": st.session_state.llm,
                                    "save_charts": True,
                                    "save_charts_path": "./charts",
                                    "verbose": False
                                }
                            )
                            
                            # Try to use query method first (more reliable for data analysis)
                            try:
                                response = df.chat(enhanced_question)
                                
                                # Add debug logging
                                print("\n=== DEBUG: Response from df.chat() ===")
                                print(f"Response type: {type(response)}")
                                print(f"Response content: {response}")
                                
                                # Function to safely convert to DataFrame
                                def ensure_dataframe(data):
                                    if isinstance(data, pd.DataFrame):
                                        return data
                                    try:
                                        if hasattr(data, 'to_dict'):
                                            data = data.to_dict()
                                        return pd.DataFrame(data)
                                    except Exception as e:
                                        print(f"Error converting to DataFrame: {e}")
                                        return None
                                
                                # Handle different response formats
                                df_to_display = None
                                title = "Data Analysis Results"
                                
                                # Case 1: Response is already a DataFrame
                                if isinstance(response, pd.DataFrame):
                                    print("\n=== DEBUG: Direct DataFrame response ===")
                                    df_to_display = response
                                    title = "Sales Data"
                                # Case 2: Response is a dictionary with 'type': 'dataframe'
                                elif isinstance(response, dict) and 'type' in response and response.get('type') == 'dataframe':
                                    print("\n=== DEBUG: Found dataframe in dictionary response ===")
                                    df_value = response.get('value')
                                    if isinstance(df_value, pd.DataFrame):
                                        df_to_display = df_value
                                        title = "Sales Data"
                                    else:
                                        df_to_display = ensure_dataframe(df_value)
                                
                                # Import re at function level to ensure it's available
                                import re
                                
                                # Process DataFrame response
                                if isinstance(response, (pd.DataFrame, dict)):
                                    try:
                                        # Extract DataFrame from response
                                        df = response if isinstance(response, pd.DataFrame) else response.get('value', response)
                                        if not isinstance(df, pd.DataFrame):
                                            df = pd.DataFrame(df)
                                        
                                        # Clean up column names
                                        df.columns = [str(col).strip().lower() for col in df.columns]
                                        
                                        # Set title based on content
                                        title = "Data Analysis Results"
                                        if 'purchase-date' in df.columns and 'quantity' in df.columns:
                                            title = "Sales Comparison"
                                            if 'compare' in user_question.lower() or 'vs' in user_question.lower():
                                                sku_match = re.search(r'sku:?\s*([\w\d-]+)', user_question.lower())
                                                if sku_match:
                                                    title = f"Sales for SKU: {sku_match.group(1)}"
                                        
                                        # Ensure numeric columns are properly typed
                                        for col in df.select_dtypes(include=['number']).columns:
                                            df[col] = pd.to_numeric(df[col], errors='coerce')
                                        
                                        # Store in session state for display
                                        if 'extracted_dataframes' not in st.session_state:
                                            st.session_state.extracted_dataframes = []
                                            
                                        st.session_state.extracted_dataframes.append({
                                            'dataframe': df,
                                            'title': title,
                                            'dataset': dataset
                                        })
                                        
                                        responses.append(f"Analysis from {dataset.capitalize()} data:")
                                        continue
                                        
                                    except Exception as e:
                                        print(f"Error processing DataFrame: {str(e)}")
                                        responses.append(f"I encountered an error processing the data: {str(e)}")
                                        continue
                                            
                                    except Exception as e:
                                        print(f"\n=== ERROR Processing DataFrame ===")
                                        print(f"Error type: {type(e).__name__}")
                                        print(f"Error message: {str(e)}")
                                        responses.append(f"I encountered an error processing the data: {str(e)}")
                                        continue
                                        
                                    except Exception as e:
                                        print(f"\n=== ERROR Processing DataFrame ===")
                                        print(f"Error type: {type(e).__name__}")
                                        print(f"Error message: {str(e)}")
                                        responses.append(f"I encountered an error processing the data: {str(e)}")
                                        continue
                                
                                # If we get here, we didn't have a DataFrame to display
                                response = str(response) if response is not None else "No data available"
                                
                                # Always try to extract tables from the response
                                df_extracted, title = extract_dataframe_from_text(response)
                                if df_extracted is not None:
                                    # Store the DataFrame in session state for rendering
                                    if 'extracted_dataframes' not in st.session_state:
                                        st.session_state.extracted_dataframes = []
                                    
                                    # Add the DataFrame and its title to the session state
                                    st.session_state.extracted_dataframes.append((df_extracted, title, dataset))
                                    
                                    # Replace the raw DataFrame text with a note that a table will be displayed
                                    response = f"I've analyzed the data and prepared a table with the results. See the table below for details."
                                else:
                                    # If no table was extracted but the response contains numeric data in a structured format,
                                    # make a second attempt with a more aggressive approach
                                    if re.search(r'\d+\s+\d+', response) or '  ' in response:
                                        # Try to find all sections that look like tables
                                        sections = re.split(r'\n\s*\n', response)
                                        for section in sections:
                                            if re.search(r'\d+\s+\d+', section) or '  ' in section:
                                                # Create a simple two-column table from this section
                                                lines = [line.strip() for line in section.split('\n') if line.strip()]
                                                if len(lines) >= 2:
                                                    # Try to extract a table from just this section
                                                    section_df, section_title = extract_dataframe_from_text(section)
                                                    if section_df is not None:
                                                        if 'extracted_dataframes' not in st.session_state:
                                                            st.session_state.extracted_dataframes = []
                                                        st.session_state.extracted_dataframes.append((section_df, section_title, dataset))
                                                        
                                                        # Replace this section in the response
                                                        response = response.replace(section, "I've prepared a table with these results. See below.")
                                                        break
                                
                                # Check for generated charts
                                chart_path = "./charts/chart.png"
                                chart_html = ""
                                if os.path.exists(chart_path):
                                    # Display the chart
                                    chart_html = f"\n\n![Generated Chart]({chart_path})"
                                    # Don't remove the chart file as Streamlit needs it to display
                                
                                responses.append(f"Analysis from {dataset.capitalize()} data:\n{response}{chart_html}")
                            except Exception as e:
                                # Check if the exception contains a DataFrame response
                                error_str = str(e)
                                if "dataframe" in error_str.lower() and "value" in error_str.lower():
                                    try:
                                        # Try to extract the DataFrame from the error message
                                        import ast
                                        # Clean up the error string to make it a valid dictionary
                                        clean_error = error_str.replace("'", '"')
                                        # Find the start of the JSON-like structure
                                        start_idx = clean_error.find('{')
                                        if start_idx >= 0:
                                            clean_error = clean_error[start_idx:]
                                            # Find the end of the JSON-like structure
                                            end_idx = clean_error.rfind('}')
                                            if end_idx >= 0:
                                                clean_error = clean_error[:end_idx+1]
                                                # Try to parse as JSON
                                                import json
                                                try:
                                                    error_dict = json.loads(clean_error)
                                                except:
                                                    # Fall back to ast.literal_eval if JSON parsing fails
                                                    try:
                                                        error_dict = ast.literal_eval(clean_error)
                                                    except:
                                                        # If both fail, try to extract using regex
                                                        import re
                                                        match = re.search(r'\{[^\{\}]*\}', clean_error)
                                                        if match:
                                                            try:
                                                                error_dict = json.loads(match.group(0))
                                                            except:
                                                                error_dict = None
                                                        else:
                                                            error_dict = None
                                        else:
                                            error_dict = None
                                        
                                        if isinstance(error_dict, dict) and error_dict.get('type') == 'dataframe':
                                            df_value = error_dict.get('value')
                                            
                                            # Handle different types of DataFrame values
                                            if isinstance(df_value, pd.DataFrame):
                                                # Already a DataFrame, use it directly
                                                pass
                                            elif isinstance(df_value, dict):
                                                # Convert dict to DataFrame
                                                try:
                                                    df_value = pd.DataFrame(df_value)
                                                except:
                                                    # If conversion fails, try to extract data differently
                                                    try:
                                                        # Try to handle the case where it's a dict with column names as keys
                                                        # and lists of values
                                                        df_value = pd.DataFrame(df_value)
                                                    except:
                                                        # If all else fails, create a simple two-column DataFrame
                                                        data = [(k, v) for k, v in df_value.items()]
                                                        df_value = pd.DataFrame(data, columns=['Key', 'Value'])
                                            elif isinstance(df_value, str):
                                                # Try to parse the string representation of a DataFrame
                                                try:
                                                    # First attempt: Try to extract using our extract_dataframe_from_text function
                                                    extracted_df, _ = extract_dataframe_from_text(df_value)
                                                    if extracted_df is not None:
                                                        df_value = extracted_df
                                                    else:
                                                        # Second attempt: Try to parse as a simple CSV-like string
                                                        lines = [line.strip() for line in df_value.strip().split('\n')]
                                                        if len(lines) >= 2:
                                                            header = [col.strip() for col in lines[0].split()]
                                                            data = []
                                                            for line in lines[1:]:
                                                                values = [val.strip() for val in line.split()]
                                                                if len(values) == len(header):
                                                                    data.append(values)
                                                            if data:
                                                                df_value = pd.DataFrame(data, columns=header)
                                                            else:
                                                                # Create a simple DataFrame with the string as content
                                                                df_value = pd.DataFrame([['Result', df_value]], columns=['Key', 'Value'])
                                                        else:
                                                            # Create a simple DataFrame with the string as content
                                                            df_value = pd.DataFrame([['Result', df_value]], columns=['Key', 'Value'])
                                                except:
                                                    # If all parsing fails, create a simple DataFrame with the string
                                                    df_value = pd.DataFrame([['Result', df_value]], columns=['Key', 'Value'])
                                            else:
                                                # For any other type, try to convert to a simple DataFrame
                                                try:
                                                    df_value = pd.DataFrame(df_value)
                                                except:
                                                    # If conversion fails, create a simple DataFrame with string representation
                                                    df_value = pd.DataFrame([['Result', str(df_value)]], columns=['Key', 'Value'])
                                            
                                            # Store the DataFrame in session state for rendering
                                            if 'extracted_dataframes' not in st.session_state:
                                                st.session_state.extracted_dataframes = []
                                            
                                            # Determine a title based on the DataFrame columns
                                            title = "Data Analysis Results"
                                            
                                            # Check for specific column combinations
                                            cols_lower = [col.lower() if isinstance(col, str) else str(col).lower() for col in df_value.columns]
                                            
                                            # Handle specific cases based on column names and user question
                                            if any(col in cols_lower for col in ['year', 'purchase-date']) and 'quantity' in cols_lower:
                                                if is_comparison_question:
                                                    title = "Sales Comparison Across Years"
                                                    
                                                    # Check if this is a specific SKU comparison
                                                    if 'sku' in user_question.lower() or 'product' in user_question.lower():
                                                        # Extract SKU from question if present
                                                        sku_match = re.search(r'sku:?\s*([\w\d-]+)', user_question.lower())
                                                        if sku_match:
                                                            sku = sku_match.group(1)
                                                            title = f"Sales Comparison for SKU: {sku}"
                                                else:
                                                    title = "Sales by Time Period"
                                            elif 'sku' in cols_lower and 'quantity' in cols_lower:
                                                title = "Top Products by Quantity"
                                            
                                            # Add the DataFrame and its title to the session state
                                            st.session_state.extracted_dataframes.append((df_value, title, dataset))
                                            
                                            # Add a response about the table with more specific information
                                            response_message = f"Analysis from {dataset.capitalize()} data:\n"
                                            
                                            # Add context-specific message based on the title
                                            if "SKU:" in title:
                                                sku = title.split("SKU:")[-1].strip()
                                                response_message += f"I've analyzed the sales data for {sku} and prepared a comparison table showing quantities across different years. "
                                                
                                                # Try to add insights if possible
                                                try:
                                                    if len(df_value) > 1:
                                                        # Sort by year to make comparison easier
                                                        df_value = df_value.sort_values('purchase-date' if 'purchase-date' in df_value.columns else 'Year')
                                                        
                                                        # Calculate year-over-year change if possible
                                                        qty_values = df_value['quantity'].astype(int).tolist()
                                                        if len(qty_values) >= 2:
                                                            change = qty_values[-1] - qty_values[-2]
                                                            pct_change = (change / qty_values[-2] * 100) if qty_values[-2] > 0 else 0
                                                            
                                                            if change > 0:
                                                                response_message += f"Sales increased by {change} units ({pct_change:.1f}%) from the previous period."
                                                            elif change < 0:
                                                                response_message += f"Sales decreased by {abs(change)} units ({abs(pct_change):.1f}%) from the previous period."
                                                            else:
                                                                response_message += "Sales remained the same across the compared periods."
                                                except:
                                                    pass
                                            elif "Comparison" in title:
                                                response_message += "I've prepared a comparison table showing sales data across different years. "
                                            elif "Top Products" in title:
                                                response_message += "I've identified the top-selling products based on quantity and prepared a table with the results. "
                                            else:
                                                response_message += "I've analyzed the data and prepared a table with the results. "
                                                
                                            response_message += "See the table below for details."
                                            responses.append(response_message)
                                            continue  # Skip the error handling below
                                    except Exception as extract_error:
                                        # If extraction fails, continue with normal error handling
                                        pass
                                        
                                # Check if the error contains a DataFrame response
                                if hasattr(e, 'args') and len(e.args) > 0 and isinstance(e.args[0], dict) and e.args[0].get('type') == 'dataframe':
                                    df_value = e.args[0].get('value')
                                    if isinstance(df_value, pd.DataFrame):
                                        # Store the DataFrame in session state for rendering
                                        if 'extracted_dataframes' not in st.session_state:
                                            st.session_state.extracted_dataframes = []
                                        
                                        # Determine a title based on the DataFrame columns and question
                                        title = "Data Analysis Results"
                                        if 'purchase-date' in df_value.columns and 'quantity' in df_value.columns:
                                            title = "Sales by Year"
                                            
                                            # Add context from the user's question
                                            if 'compare' in user_question.lower() or 'vs' in user_question.lower():
                                                title = "Sales Comparison"
                                                
                                                # Try to add SKU to title if mentioned in question
                                                sku_match = re.search(r'sku:?\s*([\w\d-]+)', user_question.lower())
                                                if sku_match:
                                                    sku = sku_match.group(1)
                                                    title = f"Sales for SKU: {sku}"
                                        
                                        st.session_state.extracted_dataframes.append((df_value, title, dataset))
                                        responses.append(f"I've analyzed the data and prepared a table with the results. See the table below for details.")
                                        continue
                                    
                                # If we get here, it's a different type of error
                                st.error(f"Error processing question with AI: {str(e)}")
                                
                                # If chat fails, try a more direct approach with specific prompting
                                try:
                                    if dataset == 'sales' and is_best_selling_question:
                                        # For best-selling questions on sales data, use a more direct approach
                                        sales_df = st.session_state.data_dict[dataset]
                                        
                                        # Handle comparison questions between years
                                        if is_comparison_question and len(years_mentioned) >= 2:
                                            # This is a comparison question between specific years
                                            comparison_results = []
                                            
                                            for year in years_mentioned:
                                                # Filter data for this year
                                                year_df = sales_df[sales_df['Year'] == year]
                                                
                                                if len(year_df) > 0 and 'sku' in year_df.columns:
                                                    # Group by SKU and sum quantities
                                                    sku_sales = year_df.groupby('sku')['quantity'].sum().reset_index()
                                                    top_sku = sku_sales.sort_values('quantity', ascending=False).head(5)
                                                    
                                                    if not top_sku.empty:
                                                        comparison_results.append((year, top_sku))
                                                    else:
                                                        responses.append(f"No sales data available for {year}.")
                                                else:
                                                    responses.append(f"No sales data available for {year}.")
                                            
                                            # Format comparison response
                                            if len(comparison_results) >= 2:
                                                response = "Comparison of top selling SKUs by year:\n\n"
                                                
                                                # Create a better formatted table for comparison
                                                response += "| Rank | "
                                                for year, _ in comparison_results:
                                                    response += f"SKU ({year}) | Quantity | "
                                                response += "\n|---|" + "|---|---|" * len(comparison_results) + "\n"
                                                
                                                # Add rows for each rank (1-5)
                                                for rank in range(5):
                                                    if rank < min(len(top_sku) for _, top_sku in comparison_results):
                                                        response += f"| {rank+1} | "
                                                        for _, top_sku in comparison_results:
                                                            sku = top_sku.iloc[rank]['sku']
                                                            qty = int(top_sku.iloc[rank]['quantity'])
                                                            response += f"{sku} | {qty} | "
                                                        response += "\n"
                                                
                                                response += "\n"
                                                
                                                # Add insights about changes between years
                                                if len(comparison_results) == 2:
                                                    year1, top_sku1 = comparison_results[0]
                                                    year2, top_sku2 = comparison_results[1]
                                                    
                                                    # Check if the top SKU changed
                                                    top_sku1_name = top_sku1.iloc[0]['sku']
                                                    top_sku2_name = top_sku2.iloc[0]['sku']
                                                    
                                                    if top_sku1_name == top_sku2_name:
                                                        response += f"**Key Insight:** {top_sku1_name} remained the top selling SKU in both {year1} and {year2}.\n"
                                                    else:
                                                        response += f"**Key Insight:** The top selling SKU changed from {top_sku1_name} in {year1} to {top_sku2_name} in {year2}.\n"
                                                    
                                                    # Find SKUs that appear in both years' top 5
                                                    skus1 = set(top_sku1['sku'])
                                                    skus2 = set(top_sku2['sku'])
                                                    common_skus = skus1.intersection(skus2)
                                                    
                                                    if common_skus:
                                                        response += f"\n**Consistent performers:** {', '.join(common_skus)} appeared in the top 5 for both years.\n"
                                                    else:
                                                        response += "\n**Complete turnover:** None of the top 5 SKUs from one year remained in the top 5 the following year.\n"
                                                
                                                responses.append(f"Analysis from {dataset.capitalize()} data:\n{response}")
                                            else:
                                                responses.append(f"Analysis from {dataset.capitalize()} data:\nInsufficient data to make a comparison between the requested years.")
                                        else:
                                            # Regular best-selling question for a single year
                                            # Extract year from question if present
                                            year_match = None
                                            if years_mentioned:
                                                year_match = years_mentioned[0]
                                            
                                            # Filter by year if specified
                                            if year_match:
                                                sales_df = sales_df[sales_df['Year'] == year_match]
                                            
                                            # Group by SKU and sum quantities
                                            if 'sku' in sales_df.columns:
                                                sku_sales = sales_df.groupby('sku')['quantity'].sum().reset_index()
                                                top_sku = sku_sales.sort_values('quantity', ascending=False).head(5)
                                                
                                                # Format the response
                                                if not top_sku.empty:
                                                    year_str = f" in {year_match}" if year_match else ""
                                                    response = f"The best selling SKU{year_str} is {top_sku.iloc[0]['sku']} with {int(top_sku.iloc[0]['quantity'])} units sold.\n\nTop 5 SKUs by sales volume:\n"
                                                    for i, row in top_sku.iterrows():
                                                        response += f"- {row['sku']}: {int(row['quantity'])} units\n"
                                                    responses.append(f"Analysis from {dataset.capitalize()} data:\n{response}")
                                                else:
                                                    responses.append(f"Analysis from {dataset.capitalize()} data:\nNo sales data available{' for the year ' + str(year_match) if year_match else ''}.")
                                            else:
                                                responses.append(f"Analysis from {dataset.capitalize()} data:\nCould not find SKU column in the sales data.")
                                    else:
                                        # For other questions, provide a helpful error message
                                        responses.append(f"Analysis from {dataset.capitalize()} data:\nI encountered an error analyzing this data. Please try rephrasing your question to be more specific.")
                                except Exception as inner_e:
                                    responses.append(f"Analysis from {dataset.capitalize()} data:\nError processing your question: {str(inner_e)}")
                        except Exception as e:
                            responses.append(f"Error analyzing {dataset} data: {str(e)}")
                    
                    # If all responses are error messages, add a helpful suggestion
                    if all("error" in response.lower() or "unfortunately" in response.lower() for response in responses if not response.startswith("Note:")):
                        responses.append("\nTip: Try asking a more specific question about the data. For example:\n- What was the best selling SKU in 2024?\n- What are the top return reasons in 2023?\n- How many units of product X were sold in 2025?")
                    
                    # Combine responses
                    final_response = "\n\n".join(responses)
                    
                    # No need to format the final response here as we'll display tables separately
                    
                    # Add information about response time
                    elapsed_time = time.time() - start_time
                    time_info = f"\n\n---\n*Response generated in {elapsed_time:.2f} seconds*"
                    final_response += time_info
                    
                    # Handle AI response display
                    if 'extracted_dataframes' in st.session_state and st.session_state.extracted_dataframes:
                        print("\n=== Processing AI response ===")
                        
                        # Get the first dataframe (assuming one response at a time for simplicity)
                        item = st.session_state.extracted_dataframes[0]
                        
                        try:
                            # Get dataframe and metadata
                            if isinstance(item, dict):
                                df = item.get('dataframe')
                                title = item.get('title', 'Analysis Results')
                            else:
                                df, title, _ = item if len(item) > 2 else (item[0], 'Analysis Results', None)
                            
                            print(f"DataFrame type: {type(df)}")
                            print(f"Title: {title}")
                            
                            if df is not None and not df.empty:
                                if not isinstance(df, pd.DataFrame):
                                    df = pd.DataFrame(df)
                                
                                print(f"DataFrame shape: {df.shape}")
                                print(f"DataFrame columns: {df.columns.tolist()}")
                                
                                # Format the dataframe as a clean markdown table
                                table_header = f"### {title}\n\n"
                                table_header += "| " + " | ".join(df.columns) + " |\n"
                                table_header += "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
                                
                                # Add each row to the table
                                table_rows = []
                                for _, row in df.iterrows():
                                    table_rows.append("| " + " | ".join(str(cell) for cell in row) + " |")
                                
                                # Combine header and rows
                                formatted_table = table_header + "\n".join(table_rows)
                                
                                # Add the formatted table to the response
                                final_response += f"\n\n{formatted_table}"
                                
                                # Add download button for full data
                                csv = df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="Download Data as CSV",
                                    data=csv,
                                    file_name=f"{title.lower().replace(' ', '_')}.csv",
                                    mime='text/csv',
                                    key=f"dl_{hash(str(df.values.tolist()))}"
                                )
                                
                                print("Response processed")
                        
                        except Exception as e:
                            error_msg = f"Error processing response: {str(e)}"
                            print(error_msg)
                            final_response += "\n\nThere was an error displaying the response data."
                        
                        # Clear the temporary extracted_dataframes
                        st.session_state.extracted_dataframes = []
                    
                    # Display the final response in the chat
                    if final_response:
                        with st.chat_message("assistant"):
                            st.write(final_response)
                    else:
                        with st.chat_message("assistant"):
                            st.write("I couldn't generate a response. Please try again.")
                            print("No response data to display")
                    
                    # Cache the response
                    st.session_state.response_cache[cache_key] = final_response
                    
                    # Add AI response to chat history
                    st.session_state.chat_history.append(("ai", final_response))
                    
                    # Rerun to update the UI with the new chat history
                    st.rerun()
                    
            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.session_state.chat_history.append(("ai", error_message))
                st.rerun()
    
    # Add a button to clear chat history
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# For testing the module directly
if __name__ == "__main__":
    ai_chat_page()
