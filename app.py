import streamlit as st
import pandas as pd
from statement_parser import BankStatementParser

st.set_page_config(page_title="Bank Statement Parser", layout="wide")

st.title("Bank Statement to CSV")
st.markdown("""
Upload your bank statement PDF. The application will attempt to extract transactions and provide a CSV download.
**Note:** This runs locally in your browser/server session. No data is sent to external parties.
""")

extraction_mode = st.radio("Extraction Mode", ["Transactions", "Loan Balance"])

uploaded_files = st.file_uploader("Choose PDF file(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    # If a single file is uploaded via the UI but accept_multiple_files=True, it returns a list.
    # Just to be safe, we iterate.

    st.write(f"Processing {len(uploaded_files)} file(s)...")

    parser = BankStatementParser()
    all_dfs = []

    # Progress indicator
    status_container = st.status("Processing files...", expanded=True)

    for uploaded_file in uploaded_files:
        status_container.write(f"Processing {uploaded_file.name}...")
        try:
            # Parse
            if extraction_mode == "Loan Balance":
                df = parser.parse_loan_balance(uploaded_file)
                entity_name = "loan balances"
            else:
                df = parser.parse(uploaded_file)
                entity_name = "transactions"

            if not df.empty:
                all_dfs.append(df)
                status_container.write(f":white_check_mark: {uploaded_file.name}: Extracted {len(df)} {entity_name}.")
            else:
                status_container.write(f":warning: {uploaded_file.name}: No {entity_name} found.")

        except Exception as e:
            status_container.write(f":x: {uploaded_file.name}: Error - {e}")

    status_container.update(label="Processing complete!", state="complete", expanded=False)

    if all_dfs:
        try:
            # Concatenate
            final_df = pd.concat(all_dfs, ignore_index=True)

            # Deduplicate (Prefer 'newer' = keep='last' because we appended in order)
            if extraction_mode == "Loan Balance":
                final_df = final_df.drop_duplicates(subset=['Date', 'Balance'], keep='last')
            else:
                # Assuming Date, Amount, Description define uniqueness.
                final_df = final_df.drop_duplicates(subset=['Date', 'Amount', 'Description'], keep='last')

            # Sort by Date
            # Convert to datetime for sorting
            # We use a temporary column to sort, to avoid breaking the original string format if not desired,
            # BUT usually standardizing the date format is good.
            # Let's try to convert 'Date' to datetime.
            final_df['Date_Obj'] = pd.to_datetime(final_df['Date'], errors='coerce')

            # Sort
            final_df = final_df.sort_values(by='Date_Obj')

            # Drop the temporary object column
            final_df = final_df.drop(columns=['Date_Obj'])

            entity_name = "loan balances" if extraction_mode == "Loan Balance" else "transactions"
            st.success(f"Successfully merged data! Total unique {entity_name}: {len(final_df)}")

            st.subheader("Preview")
            st.dataframe(final_df)

            csv = final_df.to_csv(index=False).encode('utf-8')

            st.download_button(
                label="Download Merged CSV",
                data=csv,
                file_name="merged_bank_statement.csv",
                mime='text/csv',
            )
        except Exception as e:
            st.error(f"Error merging data: {e}")

    else:
        st.warning("No valid transactions extracted from any of the files.")
