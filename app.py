import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sangrur Master Search & Filter", layout="wide")

@st.cache_data
def load_all_data():
    all_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not all_files:
        return None

    combined_df = pd.DataFrame()

    for file in all_files:
        try:
            temp_df = pd.read_csv(file)
            temp_df.columns = temp_df.columns.str.strip()
            # Track which file the data came from
            temp_df['SOURCE_FILE'] = file

            for col in ['ACCOUNT_NO', 'LEGACYACCTID', 'ACCTID']:
                if col in temp_df.columns:
                    temp_df[col] = temp_df[col].astype(str).str.strip().str.split('.').str[0]
                    if col != 'ACCOUNT_NO':
                        temp_df = temp_df.rename(columns={col: 'ACCOUNT_NO'})

            if combined_df.empty:
                combined_df = temp_df
            else:
                if 'ACCOUNT_NO' in combined_df.columns and 'ACCOUNT_NO' in temp_df.columns:
                    combined_df = pd.merge(combined_df, temp_df, on='ACCOUNT_NO', how='outer', suffixes=('', '_dup'))
                else:
                    combined_df = pd.concat([combined_df, temp_df], ignore_index=True)
        except Exception as e:
            st.warning(f"Error reading {file}: {e}")

    combined_df = combined_df.loc[:, ~combined_df.columns.str.contains('_dup')]
    return combined_df

df = load_all_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("📍 Filter Results")

if df is not None:
    # 1. Filter by SubDivision
    if 'SubDivision' in df.columns:
        subs = ["All SubDivisions"] + sorted(df['SubDivision'].dropna().unique().tolist())
        selected_sub = st.sidebar.selectbox("Select SubDivision:", subs)
    else:
        selected_sub = "All SubDivisions"

    # 2. Filter by File Name
    files = ["All Files"] + sorted(df['SOURCE_FILE'].dropna().unique().tolist())
    selected_file = st.sidebar.selectbox("Select Data File:", files)

# --- MAIN INTERFACE ---
st.title("⚡ Sangrur Division Search Portal")

if df is not None:
    # Apply Sidebar Filters to the data before searching
    filtered_df = df.copy()
    if selected_sub != "All SubDivisions":
        filtered_df = filtered_df[filtered_df['SubDivision'] == selected_sub]
    if selected_file != "All Files":
        filtered_df = filtered_df[filtered_df['SOURCE_FILE'] == selected_file]

    search_input = st.text_input("Enter Search Details (Ex: 'gt41 10144'):")

    if search_input:
        search_words = search_input.lower().split()
        row_strings = filtered_df.astype(str).apply(lambda x: ' '.join(x).lower(), axis=1)
        mask = row_strings.apply(lambda row: all(word in row for word in search_words))
        results = filtered_df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} records in {selected_sub if selected_sub != 'All SubDivisions' else 'all areas'}.")
            for _, row in results.iterrows():
                with st.expander(f"👤 {row.get('NAME', 'N/A')} | SAP ID: {row.get('ACCOUNT_NO', 'N/A')}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**Account ID:** `{row.get('ACCOUNT_NO')}`")
                        st.write(f"**Legacy ID:** `{row.get('LEGACYACCTID', row.get('OLD_LEGACY_ID', 'N/A'))}`")
                        st.write(f"**SubDivision:** {row.get('SubDivision', 'N/A')}")
                    with c2:
                        st.write(f"**Meter:** `{row.get('METER_NUMBER', row.get('MTR_SER_NO', 'N/A'))}`")
                        st.write(f"**MRU:** {row.get('Village/MRU', 'N/A')}")
                        st.write(f"**Source File:** {row.get('SOURCE_FILE')}")
                    with c3:
                        st.write(f"**Address:** {row.get('ADDRESS', 'N/A')}")
                        if pd.notnull(row.get('LATITUDE')):
                            st.link_button("🌐 Map", f"https://www.google.com/maps?q={row['LATITUDE']},{row['LONGITUDE']}")
        else:
            st.warning("No records found with these filters. Try changing 'All SubDivisions'.")
