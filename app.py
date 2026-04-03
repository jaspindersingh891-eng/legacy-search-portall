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
            
            # 1. IDENTIFY IDs: We look for SAP and Legacy numbers
            # We standardize them so they show up in every result
            if 'ACCOUNT_NO' in temp_df.columns:
                 temp_df['SAP_ID'] = temp_df['ACCOUNT_NO'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            
            # Look for Legacy ID in common column names
            for leg_col in ['LEGACYACCTID', 'ACCTID', 'OLD_ACCOUNT', 'LEGACY_ID']:
                if leg_col in temp_df.columns:
                    temp_df['LEGACY_ID'] = temp_df[leg_col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    break

            # 2. Standardize Meter Number
            if 'METER_NUMBER' not in temp_df.columns and 'MTR_SER_NO' in temp_df.columns:
                temp_df = temp_df.rename(columns={'MTR_SER_NO': 'METER_NUMBER'})

            temp_df['SOURCE_FILE'] = file
            temp_df = make_columns_unique(temp_df)
            data_list.append(temp_df)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

    if not data_list:
        return None

    # Stack all files into one master database
    return pd.concat(data_list, axis=0, ignore_index=True, sort=False)

# --- USER INTERFACE ---
st.title("⚡ Master Search Portal")
st.markdown("Enter any detail to find **SAP ID** and **Legacy ID** together.")

df = load_all_data()

if df is not None:
    search_input = st.text_input("Search (Ex: 'gt41 410144' or a Name):", placeholder="Start typing...")

    if search_input:
        search_words = search_input.lower().split()
        
        # Search across key columns
        search_cols = ['NAME', 'ADDRESS', 'SAP_ID', 'LEGACY_ID', 'METER_NUMBER', 'Village/MRU']
        available_cols = [c for c in search_cols if c in df.columns]
        
        row_strings = df[available_cols].astype(str).apply(lambda x: ' '.join(x).lower(), axis=1)
        mask = row_strings.apply(lambda row: all(word in row for word in search_words))
        results = df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} matching records.")
            for _, row in results.iterrows():
                # Displaying both IDs clearly in the Expander Title
                sap = row.get('SAP_ID', 'N/A')
                legacy = row.get('LEGACY_ID', 'N/A')
                name = row.get('NAME', 'N/A')
                
                with st.expander(f"👤 {name} | SAP: {sap} | Legacy: {legacy}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.subheader("🆔 Account IDs")
                        st.write(f"**SAP Account No:** `{sap}`")
                        st.write(f"**Legacy Account:** `{legacy}`")
                        st.write(f"**SubDivision:** {row.get('SubDivision', 'N/A')}")
                    with c2:
                        st.subheader("⚡ Meter & Contact")
                        st.write(f"**Meter Serial:** `{row.get('METER_NUMBER', 'N/A')}`")
                        st.write(f"**Phone:** {row.get('PHONE', 'N/A')}")
                        st.write(f"**MRU:** {row.get('Village/MRU', 'N/A')}")
                    with c3:
                        st.subheader("📍 Location")
                        st.write(f"**Address:** {row.get('ADDRESS', 'N/A')}")
                        if pd.notnull(row.get('LATITUDE')):
                            st.link_button("🌐 View on Google Maps", f"https://www.google.com/maps?q={row['LATITUDE']},{row['LONGITUDE']}")
        else:
            st.warning("No matches found. Try searching for just the numbers.")
