import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sangrur Division Master Search", layout="wide")

def make_columns_unique(df):
    """Force all columns in a dataframe to be unique to prevent crashes."""
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
            temp_df = pd.read_csv(file, low_memory=False)
            temp_df.columns = temp_df.columns.str.strip()
            
            # 1. Standardize IDs
            if 'ACCOUNT_NO' in temp_df.columns:
                 temp_df['SAP_ID'] = temp_df['ACCOUNT_NO'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            
            for leg_col in ['LEGACYACCTID', 'ACCTID', 'OLD_ACCOUNT', 'LEGACY_ID']:
                if leg_col in temp_df.columns:
                    temp_df['LEGACY_ID'] = temp_df[leg_col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    break

            # 2. Standardize Meter & Division
            if 'MTR_SER_NO' in temp_df.columns:
                temp_df = temp_df.rename(columns={'MTR_SER_NO': 'METER_NUMBER'})

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

# --- SIDEBAR FILTERS ---
st.sidebar.header("📍 Division Filter")
selected_division = "All Divisions"

if df is not None:
    # Look for 'Division' column in your data
    if 'Division' in df.columns:
        div_list = ["All Divisions"] + sorted(df['Division'].dropna().unique().tolist())
        selected_division = st.sidebar.selectbox("Select Division:", div_list)
    else:
        st.sidebar.warning("No 'Division' column found in CSV files.")

# --- MAIN INTERFACE ---
st.title("⚡ Master Search Portal")
st.markdown(f"Current Filter: **{selected_division}**")

if df is not None:
    # Apply Division Filter
    filtered_df = df.copy()
    if selected_division != "All Divisions":
        filtered_df = filtered_df[filtered_df['Division'] == selected_division]

    search_input = st.text_input("Search (Ex: 'gt41 410144' or a Name):", placeholder="Start typing...")

    if search_input:
        search_words = search_input.lower().split()
        search_cols = ['NAME', 'ADDRESS', 'SAP_ID', 'LEGACY_ID', 'METER_NUMBER', 'Village/MRU', 'SubDivision']
        available_cols = [c for c in search_cols if c in filtered_df.columns]
        
        row_strings = filtered_df[available_cols].astype(str).apply(lambda x: ' '.join(x).lower(), axis=1)
        mask = row_strings.apply(lambda row: all(word in row for word in search_words))
        results = filtered_df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} records in {selected_division}.")
            for _, row in results.iterrows():
                sap = row.get('SAP_ID', 'N/A')
                legacy = row.get('LEGACY_ID', 'N/A')
                
                with st.expander(f"👤 {row.get('NAME', 'N/A')} | SAP: {sap} | Legacy: {legacy}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.subheader("🆔 Account IDs")
                        st.write(f"**SAP Account No:** `{sap}`")
                        st.write(f"**Legacy Account:** `{legacy}`")
                        st.write(f"**Division:** {row.get('Division', 'N/A')}")
                    with c2:
                        st.subheader("⚡ Meter & MRU")
                        st.write(f"**Meter Serial:** `{row.get('METER_NUMBER', 'N/A')}`")
                        st.write(f"**MRU/Village:** {row.get('Village/MRU', 'N/A')}")
                        st.write(f"**SubDivision:** {row.get('SubDivision', 'N/A')}")
                    with c3:
                        st.subheader("📍 Location")
                        st.write(f"**Address:** {row.get('ADDRESS', 'N/A')}")
                        if pd.notnull(row.get('LATITUDE')):
                            st.link_button("🌐 View on Google Maps", f"https://www.google.com/maps?q={row['LATITUDE']},{row['LONGITUDE']}")
        else:
            st.warning(f"No matches found in {selected_division}. Try selecting 'All Divisions'.")
