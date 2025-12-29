import pdfplumber
import pandas as pd
import re
import io

class BankStatementParser:
    def __init__(self):
        pass

    def extract_account_number(self, text):
        """
        Attempts to find an account number in the text.
        """
        # Common patterns for account numbers
        patterns = [
            r"Account\s*Number\s*[:#]?\s*(\d+)",
            r"Account\s*#\s*[:]?\s*(\d+)",
            r"Acct\s*#\s*[:]?\s*(\d+)",
            r"Account\s*:\s*(\d+)",
            r"Account\s*(\d{8,})" # Standalone account number often 8+ digits
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def parse(self, pdf_file) -> pd.DataFrame:
        """
        Parses a PDF file object and returns a pandas DataFrame.
        """
        transactions = []
        account_number = None

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()

                # Try to find account number if not already found
                if not account_number and text:
                    account_number = self.extract_account_number(text)

                # Try to extract tables
                tables = page.extract_tables()

                if tables:
                    for table in tables:
                        df = self._process_table(table)
                        if df is not None:
                             transactions.append(df)
                else:
                    # Fallback to text parsing if no tables found (simplified)
                    pass

        if transactions:
            final_df = pd.concat(transactions, ignore_index=True)
            if account_number:
                final_df['Account'] = account_number
            else:
                 if 'Account' not in final_df.columns:
                     final_df['Account'] = 'Unknown'

            # Ensure required columns exist
            required_cols = ['Date', 'Amount', 'Account']
            for col in required_cols:
                if col not in final_df.columns:
                    final_df[col] = None # Or empty string

            # Reorder
            cols = ['Account', 'Date', 'Amount'] + [c for c in final_df.columns if c not in ['Account', 'Date', 'Amount']]
            return final_df[cols]
        else:
            return pd.DataFrame(columns=['Account', 'Date', 'Amount'])

    def _process_table(self, table) -> pd.DataFrame:
        """
        Heuristic to identify Date and Amount columns in a table.
        """
        if not table:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(table)

        # Identify header
        # Assumption: First row is header if it contains string "Date" or "Amount"
        header_row_idx = -1
        for i, row in df.iterrows():
            row_text = " ".join([str(x) for x in row if x]).lower()
            if "date" in row_text and ("amount" in row_text or "debit" in row_text or "credit" in row_text):
                header_row_idx = i
                break

        if header_row_idx != -1:
            df.columns = df.iloc[header_row_idx]
            df = df.iloc[header_row_idx+1:]

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Map columns
        date_col = None
        amount_col = None
        debit_col = None
        credit_col = None
        desc_col = None

        for col in df.columns:
            col_lower = col.lower()
            if "date" in col_lower:
                date_col = col
            elif "amount" in col_lower:
                amount_col = col
            elif "debit" in col_lower:
                debit_col = col
            elif "credit" in col_lower:
                credit_col = col
            elif "description" in col_lower or "details" in col_lower:
                desc_col = col

        # Logic to handle separate Debit/Credit columns
        if date_col:
            result = pd.DataFrame()
            result['Date'] = df[date_col]

            if debit_col and credit_col:
                # Combine Debit and Credit
                # Clean function
                def clean_money(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    val = str(val).replace(',', '').replace('$', '')
                    if val.startswith('(') and val.endswith(')'):
                        val = '-' + val[1:-1]
                    try:
                        return float(val)
                    except ValueError:
                        return 0.0

                debits = df[debit_col].apply(clean_money)
                credits = df[credit_col].apply(clean_money)

                # Assume Debit is negative, Credit is positive (common in statements, though sometimes headers say 'Debit Amount' and it's positive number representing outflow)
                # Usually standard practice: Money out (Debit) is negative balance effect, Money in (Credit) is positive.
                # However, raw numbers in columns are usually absolute values.
                # We will make Debit negative and Credit positive.

                result['Amount'] = credits - debits # If both are present, usually one is 0. If both non-zero, net them.

            elif amount_col:
                 result['Amount'] = df[amount_col]
                 # Clean Amount
                 result['Amount'] = result['Amount'].astype(str).str.replace(r'[$,]', '', regex=True)
                 # Handle (100.00) as negative
                 result['Amount'] = result['Amount'].apply(lambda x: '-' + x[1:-1] if x.startswith('(') and x.endswith(')') else x)
                 # Convert to numeric
                 result['Amount'] = pd.to_numeric(result['Amount'], errors='coerce')

            else:
                return None # No amount info found

            if desc_col:
                result['Description'] = df[desc_col]

            return result.dropna(subset=['Date', 'Amount'])

        return None
