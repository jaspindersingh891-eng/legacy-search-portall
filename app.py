import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sangrur Field Search Portal", layout="wide")

def make_columns_unique(df):
    """Ensures all columns have unique names to prevent system crashes."""
    cols = []
    count = {}
    for col in df.columns:
        if col in count:
            count[col] += 1
            cols.append(f"{col}_{count[col]}")
        else:
            count[col] = 0
            cols.append(col)
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
            temp_df.columns = temp_df.columns.str.strip()
            
            # 1. Standardize the IDs for Display
            if 'ACCOUNT_NO' in temp_df.columns:
                 temp_df['SAP_ID'] = temp_df['ACCOUNT_NO'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            
            # Map various names to 'Legacy Account'
            for leg_col in ['LEGACYACCTID', 'ACCTID', 'OLD_ACCOUNT', 'LEGACY_ID']:
                if leg_col in temp_df.columns:
                    temp_df['LEGACY_DISPLAY'] = temp_df[leg_col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    break

            # 2. Map various names to 'Meter Serial'
            if 'METER_NUMBER' in temp_df.columns:
                temp_df['METER_DISPLAY'] = temp_df['METER_NUMBER']
            elif 'MTR_SER_NO' in temp_df.columns:
                temp_df['METER_DISPLAY'] = temp_df['MTR_SER_NO']

            temp_df['SOURCE_FILE'] = file
            temp_df = make_columns_unique(temp_df)
            data_list.append(temp_df)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

    if not data_list:
        return None

    return pd.concat(data_list, axis=0, ignore_index=True, sort=False)

# --- LOAD DATA ---
df = load_all_data()

# --- SIDEBAR: SUBDIVISION FILTER ---
st.sidebar.header("📂 Filter by Area")
selected_sub = "All SubDivisions"

if df is not None and 'SubDivision' in df.columns:
    sub_options = ["All SubDivisions"] + sorted(df['SubDivision'].dropna().unique().tolist())
    selected_sub = st.sidebar.selectbox("Select SubDivision:", sub_options)

# --- MAIN INTERFACE ---
st.title("⚡ Sangrur Field Search Portal")

if df is not None:
    # Apply SubDivision Filter
    filtered_df = df.copy()
    if selected_sub != "All SubDivisions":
        filtered_df = filtered_df[filtered_df['SubDivision'] == selected_sub]

    # Smart Search Box
    search_input = st.text_input("Search Name, ID, or Address Code:", placeholder="Ex: gt41 10144")

    if search_input:
        search_words = search_input.lower().split()
        # Search columns
        search_cols = ['NAME', 'ADDRESS', 'SAP_ID', 'LEGACY_DISPLAY', 'METER_DISPLAY', 'Village/MRU']
        available_cols = [c for c in search_cols if c in filtered_df.columns]
        
        # --- FIXED SEARCH LOGIC (Line 90 Fix) ---
        # Instead of just .astype(str), we handle nulls and convert carefully
        def create_search_string(row):
            return ' '.join(row.dropna().astype(str).values).lower()

        row_strings = filtered_df[available_cols].apply(create_search_string, axis=1)
        mask = row_strings.apply(lambda row: all(word in row for word in search_words))
        results = filtered_df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} matching accounts.")
            for _, row in results.iterrows():
                with st.expander(f"👤 {row.get('NAME', 'N/A')} | SAP: {row.get('SAP_ID', 'N/A')}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Account ID (SAP):** `{row.get('SAP_ID', 'N/A')}`")
                        st.write(f"**Legacy Account:** `{row.get('LEGACY_DISPLAY', 'N/A')}`")
                        st.write(f"**Name:** {row.get('NAME', 'N/A')}")
                        st.write(f"**Address:** {row.get('ADDRESS', 'N/A')}")
                    with c2:
                        st.write(f"**MRU:** {row.get('Village/MRU', 'N/A')}")
                        st.write(f"**Meter Serial Number:** `{row.get('METER_DISPLAY', 'N/A')}`")
                        
                        if pd.notnull(row.get('LATITUDE')) and pd.notnull(row.get('LONGITUDE')):
                            st.link_button("🌐 Open Location in Google Maps", f"https://www.google.com/maps?q={row['LATITUDE']},{row['LONGITUDE']}")
                        else:
                            st.write("**Location:** Not available")
        else:
            st.warning("No matches found.")
