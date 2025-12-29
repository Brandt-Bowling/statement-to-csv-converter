import streamlit as st
import pandas as pd
from statement_parser import BankStatementParser

st.set_page_config(page_title="Bank Statement Parser", layout="wide")

st.title("Bank Statement to CSV")
st.markdown("""
Upload your bank statement PDF. The application will attempt to extract transactions and provide a CSV download.
**Note:** This runs locally in your browser/server session. No data is sent to external parties.
""")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.write(f"Processing {uploaded_file.name}...")

    parser = BankStatementParser()
    try:
        df = parser.parse(uploaded_file)

        if not df.empty:
            st.success("Successfully extracted data!")

            st.subheader("Preview")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode('utf-8')

            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"{uploaded_file.name.replace('.pdf', '')}.csv",
                mime='text/csv',
            )
        else:
            st.error("Could not find any transaction tables in the PDF. Please check if the PDF is text-based (not scanned image) and has a clear table structure.")

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
