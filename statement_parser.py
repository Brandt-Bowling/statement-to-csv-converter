import pdfplumber
import pandas as pd
import re
import io
import pytesseract
import pypdfium2 as pdfium
from PIL import Image

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
        has_text_content = False

        # Buffer for text content from pages where table extraction failed
        text_content_buffer = []

        # Reset pointer if it's a file object
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)

        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        has_text_content = True

                    # Try to find account number if not already found
                    if not account_number and text:
                        account_number = self.extract_account_number(text)

                    # Try to extract tables
                    tables = page.extract_tables()
                    page_has_tables = False

                    if tables:
                        for table in tables:
                            df = self._process_table(table)
                            if df is not None:
                                 transactions.append(df)
                                 page_has_tables = True

                    # If no tables found on this page but text exists, buffer it for text-based parsing
                    if not page_has_tables and text:
                        text_content_buffer.append(text)

        except Exception as e:
            print(f"Error reading PDF with pdfplumber: {e}")

        # Process buffered text content (from pages without tables)
        if text_content_buffer:
            print("Attempting to parse text content from pages where table extraction failed...")
            full_text = "\n".join(text_content_buffer)
            text_df = self._parse_text_lines(full_text)
            if not text_df.empty:
                transactions.append(text_df)

        # Fallback to OCR if no tables found or no text content
        if not transactions:
            print("No text/tables found. Attempting OCR...")
            ocr_df = self._parse_with_ocr(pdf_file)
            if ocr_df is not None and not ocr_df.empty:
                 # Check if we can find account number in OCR text
                 # _parse_with_ocr might return it if implemented, or we scan raw text
                 transactions.append(ocr_df)

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

    def _parse_with_ocr(self, pdf_file) -> pd.DataFrame:
        """
        Converts PDF to images, extracts text via OCR, and parses line by line.
        """
        if hasattr(pdf_file, 'read'):
            pdf_file.seek(0)
            # pypdfium2 expects bytes or path
            pdf = pdfium.PdfDocument(pdf_file)
        else:
            pdf = pdfium.PdfDocument(pdf_file)

        all_text = ""
        n_pages = len(pdf)

        for i in range(n_pages):
            page = pdf[i]
            # Render to image (scale=3 for better OCR resolution)
            bitmap = page.render(scale=3)
            image = bitmap.to_pil()

            text = pytesseract.image_to_string(image)
            all_text += text + "\n"

        return self._parse_text_lines(all_text)

    def _parse_text_lines(self, text) -> pd.DataFrame:
        """
        Parses raw text (from OCR or pdfplumber extraction).
        Supports multiple formats:
        1. Date Amount Description
        2. Date Description Amount [Balance]
        """
        lines = text.split('\n')
        data = []

        # Regex 1: Date Amount Description
        # 12/08 604.67 ACH CREDIT ...
        regex_date_amount_desc = re.compile(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+([0-9,]+\.\d{2})\s+(.*)', re.IGNORECASE)

        # Regex 2: Date Description Amount [Balance]
        # 11/25 ACH DEP... 170.00 4,919.85
        # We look for Date, then greedy match text, then Amount, then optional Balance at end
        regex_date_desc_amount = re.compile(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(.+?)\s+(-?\$?[0-9,]+\.\d{2})(?:\s+(-?\$?[0-9,]+\.\d{2}))?$', re.IGNORECASE)

        current_section_sign = 0 # 1 for credit, -1 for debit, 0 unknown

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect Section Headers
            if "DEPOSITS" in line.upper() or "CREDITS" in line.upper():
                current_section_sign = 1
            elif "DEBITS" in line.upper() or "WITHDRAWALS" in line.upper():
                current_section_sign = -1

            # Try Regex 1 (Date Amount Desc)
            match1 = regex_date_amount_desc.match(line)
            match2 = regex_date_desc_amount.match(line)

            date_str = None
            amount_str = None
            desc_str = None

            if match1:
                date_str = match1.group(1)
                amount_str = match1.group(2)
                desc_str = match1.group(3)
            elif match2:
                date_str = match2.group(1)
                desc_str = match2.group(2)
                amount_str = match2.group(3)
                # match2.group(4) is balance, ignored

            if date_str and amount_str:
                # Parse amount
                try:
                    clean_amt = amount_str.replace(',', '').replace('$', '')
                    amount = float(clean_amt)
                except ValueError:
                    continue

                # Determine sign
                sign = current_section_sign

                desc_upper = desc_str.upper()

                # Keyword override
                if "DEBIT" in desc_upper and "CREDIT" not in desc_upper:
                    sign = -1
                elif "CREDIT" in desc_upper and "DEBIT" not in desc_upper:
                    sign = 1
                elif "WITHDRAWAL" in desc_upper:
                    sign = -1
                elif "DEP" in desc_upper or "DEPOSIT" in desc_upper:
                    sign = 1
                elif "PAYMENT" in desc_upper:
                     # Usually debit
                     sign = -1

                # Apply sign
                if sign != 0:
                     amount = abs(amount) * sign

                data.append({
                    'Date': date_str,
                    'Amount': amount,
                    'Description': desc_str
                })
            else:
                # Potential multi-line description logic
                # If we just added a row, and this line doesn't look like a date, append to prev description
                # Avoid appending if it looks like a header or garbage
                if data and not re.match(r'\d{1,2}/\d{1,2}', line):
                    # Check if it looks like a continuation (indented or just text)
                    if "Summary" not in line and "Balance" not in line and "Transactions" not in line:
                         data[-1]['Description'] += " " + line

        return pd.DataFrame(data)

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
