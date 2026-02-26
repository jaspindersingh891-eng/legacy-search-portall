import streamlit as st
import pandas as pd

# 1. Page Config
st.set_page_config(page_title="Master Search Portal", layout="wide")

@st.cache_data
def load_and_merge_data():
    try:
        # Load File 1 (Legacy Mapping)
        df1 = pd.read_csv("data1.csv")
        df1.columns = df1.columns.str.strip()
        
        # Rename and force to String (Text)
        df1 = df1.rename(columns={'ACCTID': 'OLD_LEGACY_ID', 'LEGACYACCTID': 'ACCOUNT_NO'})
        df1['ACCOUNT_NO'] = df1['ACCOUNT_NO'].astype(str).str.strip().str.split('.').str[0]

        # Load File 2 (SAP & Location Details)
        df2 = pd.read_csv("data2.csv")
        df2.columns = df2.columns.str.strip()
        
        # Force to String (Text) to match File 1
        df2['ACCOUNT_NO'] = df2['ACCOUNT_NO'].astype(str).str.strip().str.split('.').str[0]

        # Merge both files on the cleaned Text column
        master_df = pd.merge(df1, df2, on='ACCOUNT_NO', how='outer', suffixes=('_f1', '_f2'))
        
        # Combine Names and Addresses
        master_df['NAME'] = master_df['NAME_f2'].fillna(master_df['NAME_f1'])
        master_df['ADDRESS'] = master_df['ADDRESS_f2'].fillna(master_df['ADDRESS_f1'])
        
        # Handle different meter column names
        m_col = 'METER_NUMBER' if 'METER_NUMBER' in master_df.columns else 'MTR_SER_NO'
        master_df['FINAL_METER'] = master_df[m_col].fillna(master_df.get('MTR_SER_NO', 'N/A'))
        
        return master_df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

df = load_and_merge_data()

# --- Search Interface ---
st.title("📂 Sangrur Master Search")
st.markdown("Search by **Account ID**, **Name**, **Meter**, or **Address Code** (e.g. `241022`)")

search_query = st.text_input("Enter Search Term:", placeholder="Start typing...")

if df is not None:
    if search_query:
        # Powerful search across all columns
        mask = df.astype(str).apply(
            lambda x: x.str.contains(search_query, case=False, na=False)
        ).any(axis=1)
        results = df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} matches")
            for _, row in results.iterrows():
                with st.expander(f"📌 {row.get('NAME', 'N/A')} | SAP: {row.get('ACCOUNT_NO', 'N/A')}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.subheader("🆔 IDs")
                        st.write(f"**SAP Account:** `{row.get('ACCOUNT_NO')}`")
                        st.write(f"**Legacy ID:** `{row.get('OLD_LEGACY_ID')}`")
                    with c2:
                        st.subheader("⚡ Meter")
                        st.write(f"**Meter No:** `{row.get('FINAL_METER')}`")
                        st.write(f"**MRU:** {row.get('Village/MRU', 'N/A')}")
                    with c3:
                        st.subheader("📍 Location")
                        st.write(f"**Address:** {row.get('ADDRESS')}")
                        if pd.notnull(row.get('LATITUDE')):
                            st.link_button("🌐 View on Map", f"https://www.google.com/maps/search/?api=1&query={row['LATITUDE']},{row['LONGITUDE']}")
        else:
            st.warning("No matches found.")
