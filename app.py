import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sangrur Division Master Search", layout="wide")

@st.cache_data
def load_all_data():
    all_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not all_files:
        return None

    data_list = []

    for file in all_files:
        try:
            # Read only the first 100 columns to prevent memory crashes if files are huge
            temp_df = pd.read_csv(file, low_memory=False)
            temp_df.columns = temp_df.columns.str.strip()
            
            # Record which file this came from
            temp_df['SOURCE_FILE'] = file

            # Standardize Account columns to a single name: 'ACCOUNT_NO'
            for col in ['ACCOUNT_NO', 'LEGACYACCTID', 'ACCTID', 'ACCOUNT_ID']:
                if col in temp_df.columns:
                    temp_df[col] = temp_df[col].astype(str).str.strip().str.split('.').str[0]
                    if col != 'ACCOUNT_NO':
                        temp_df = temp_df.rename(columns={col: 'ACCOUNT_NO'})

            # Clean Meter Number column names
            if 'MTR_SER_NO' in temp_df.columns:
                temp_df = temp_df.rename(columns={'MTR_SER_NO': 'METER_NUMBER'})

            # Add to our list for stacking
            data_list.append(temp_df)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

    if not data_list:
        return None

    # STACKING instead of MERGING (Prevents the 'suffixes' error)
    # This places files one after another in a long list
    combined_df = pd.concat(data_list, axis=0, ignore_index=True, sort=False)
    
    return combined_df

# --- WEBSITE INTERFACE ---
st.title("⚡ Master Search Portal (Fixed)")
st.markdown("Search across all files for **Account No**, **Name**, **Meter**, or **Code** (Ex: `gt41 10144`).")

df = load_all_data()

if df is not None:
    # Sidebar Filters
    st.sidebar.header("📍 Search Filters")
    
    # Subdivision Filter
    if 'SubDivision' in df.columns:
        sub_list = ["All Areas"] + sorted(df['SubDivision'].dropna().unique().tolist())
        sel_sub = st.sidebar.selectbox("Choose Area:", sub_list)
        if sel_sub != "All Areas":
            df = df[df['SubDivision'] == sel_sub]

    # Search Box
    search_input = st.text_input("Enter Details to Search:", placeholder="Start typing name or code...")

    if search_input:
        # Smart Multi-Word Search
        search_words = search_input.lower().split()
        
        # We only search key columns to keep it fast
        search_cols = ['NAME', 'ADDRESS', 'ACCOUNT_NO', 'METER_NUMBER', 'Village/MRU']
        available_cols = [c for c in search_cols if c in df.columns]
        
        # Convert search columns to one big string for each row
        row_strings = df[available_cols].astype(str).apply(lambda x: ' '.join(x).lower(), axis=1)
        mask = row_strings.apply(lambda row: all(word in row for word in search_words))
        results = df[mask]

        if not results.empty:
            st.success(f"Found {len(results)} matches.")
            for _, row in results.iterrows():
                with st.expander(f"👤 {row.get('NAME', 'N/A')} | SAP: {row.get('ACCOUNT_NO', 'N/A')}"):
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
    st.info("Upload CSV files to GitHub to begin.")
