import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sangrur Master Search", layout="wide")

def fix_duplicate_columns(df):
    """Renames duplicate columns by adding a suffix (e.g., NAME, NAME_1)"""
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): 
        cols[cols == dup] = [f"{dup}_{i}" if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    return df

@st.cache_data
def load_all_data():
    all_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not all_files:
        return None

    data_list = []

    for file in all_files:
        try:
            # Read file with low_memory=False to handle mixed data types
            temp_df = pd.read_csv(file, low_memory=False)
            
            # 1. Clean column names (strip spaces)
            temp_df.columns = temp_df.columns.str.strip()
            
            # 2. FIX DUPLICATE COLUMNS (Prevents InvalidIndexError)
            temp_df = fix_duplicate_columns(temp_df)
            
            # Record source file
            temp_df['SOURCE_FILE'] = file

            # 3. Standardize Account ID columns
            for col in ['ACCOUNT_NO', 'LEGACYACCTID', 'ACCTID', 'ACCOUNT_ID']:
                if col in temp_df.columns:
                    temp_df[col] = temp_df[col].astype(str).str.strip().str.split('.').str[0]
                    if col != 'ACCOUNT_NO':
                        temp_df = temp_df.rename(columns={col: 'ACCOUNT_NO'})

            # 4. Standardize Meter Serial Number
            if 'MTR_SER_NO' in temp_df.columns:
                temp_df = temp_df.rename(columns={'MTR_SER_NO': 'METER_NUMBER'})

            data_list.append(temp_df)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

    if not data_list:
        return None

    # Stack all files vertically
    # ignore_index=True ensures the final table has a clean 1, 2, 3... numbering
    combined_df = pd.concat(data_list, axis=0, ignore_index=True, sort=False)
    
    return combined_df

# --- WEBSITE INTERFACE ---
st.title("⚡ Master Search Portal")
st.markdown("Search for **Account No**, **Name**, **Meter**, or **Code** (Ex: `gt41 10144`).")

df = load_all_data()

if df is not None:
    # Sidebar Filters
    st.sidebar.header("📍 Search Filters")
    
    # Area Filter
    if 'SubDivision' in df.columns:
        sub_list = ["All Areas"] + sorted(df['SubDivision'].dropna().unique().tolist())
        sel_sub = st.sidebar.selectbox("Choose Area:", sub_list)
        if sel_sub != "All Areas":
            df = df[df['SubDivision'] == sel_sub]

    # Search Box
    search_input = st.text_input("Enter Search Details:", placeholder="Search name, code, or ID...")

    if search_input:
        # Smart Multi-Word Search Logic
        search_words = search_input.lower().split()
        
        # Focus search on key columns for speed
        search_cols = ['NAME', 'ADDRESS', 'ACCOUNT_NO', 'METER_NUMBER', 'Village/MRU']
        available_cols = [c for c in search_cols if c in df.columns]
        
        # Convert search columns to string and search
        row_strings = df[available_cols].astype(str).apply(lambda x: ' '.join(x).lower(), axis=1)
        mask = row_strings.apply(lambda row: all(word in row for word in search_words))
        results = df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} matching records.")
            for _, row in results.iterrows():
                with st.expander(f"👤 {row.get('NAME', 'N/A')} | SAP ID: {row.get('ACCOUNT_NO', 'N/A')}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.subheader("🆔 IDs")
                        st.write(f"**Account:** `{row.get('ACCOUNT_NO', 'N/A')}`")
                        st.write(f"**Area:** {row.get('SubDivision', 'N/A')}")
                    with c2:
                        st.subheader("⚡ Meter")
                        st.write(f"**Meter No:** `{row.get('METER_NUMBER', 'N/A')}`")
                        st.write(f"**File:** {row.get('SOURCE_FILE', 'N/A')}")
                    with c3:
                        st.subheader("📍 Location")
                        st.write(f"**Address:** {row.get('ADDRESS', 'N/A')}")
                        if pd.notnull(row.get('LATITUDE')):
                            st.link_button("🌐 Open Map", f"https://www.google.com/maps?q={row['LATITUDE']},{row['LONGITUDE']}")
        else:
            st.warning("No matches found.")
else:
    st.info("Please upload your CSV files to GitHub.")
