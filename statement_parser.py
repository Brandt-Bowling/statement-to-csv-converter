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

    def parse_loan_balance(self, pdf_file) -> pd.DataFrame:
        """
        Extracts Statement Date and Outstanding Balance from the PDF.
        Returns a DataFrame with columns: ['Date', 'Balance']
        """
        # Reset pointer if it's a file object
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)

        all_text = ""
        has_text_content = False
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
                        has_text_content = True
        except Exception as e:
            print(f"Error reading PDF with pdfplumber: {e}")

        # Fallback to OCR if no text found
        if not has_text_content:
            print("No text found. Attempting OCR for loan balance extraction...")
            try:
                all_text = self._extract_text_with_ocr(pdf_file)
            except Exception as e:
                print(f"Error extracting text with OCR: {e}")

        # Regex for Statement Date
        match_date = re.search(r"(?:Statement\s+Date|Date)\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", all_text, re.IGNORECASE)
        if not match_date:
            match_date = re.search(r"(?:Statement\s+Date|Date)[\s:]*\n[\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", all_text, re.IGNORECASE)

        date = match_date.group(1) if match_date else None

        # Regex for Outstanding Balance
        match_bal = re.search(r"outstanding\s+(?:balance|principal)[^\d]*?([0-9,]+(?:\.\d{2})?)", all_text, re.IGNORECASE)
        if match_bal:
            val = match_bal.group(1).replace(',', '')
            balance = -abs(float(val))
        else:
            balance = None

        if date or balance is not None:
            return pd.DataFrame([{'Date': date, 'Balance': balance}])
        else:
            return pd.DataFrame(columns=['Date', 'Balance'])

    def _extract_text_with_ocr(self, pdf_file) -> str:
        """
        Converts PDF to images and extracts raw text via OCR.
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
        return all_text

    def _parse_with_ocr(self, pdf_file) -> pd.DataFrame:
        """
        Converts PDF to images, extracts text via OCR, and parses line by line.
        """
        all_text = self._extract_text_with_ocr(pdf_file)
        return self._parse_text_lines(all_text)

    def _clean_money(self, val):
        if not val:
            return 0.0
        val = str(val).replace(',', '').replace('$', '')
        if val.startswith('(') and val.endswith(')'):
            val = '-' + val[1:-1]
        try:
            return float(val)
        except ValueError:
            return 0.0

    def _parse_text_lines(self, text) -> pd.DataFrame:
        """
        Parses raw text (from OCR or pdfplumber extraction).
        Uses a robust Right-to-Left strategy to identify amounts and balances.
        """
        lines = text.split('\n')
        data = []

        # Regex to find money-like patterns
        # Matches: $1,234.56, -123.45, (123.45), 123.45
        money_pattern = re.compile(r'(?:-?\$?[0-9,]+\.\d{2}|\(\$?[0-9,]+\.\d{2}\))')

        # Regex for Date at start
        date_pattern = re.compile(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)')

        current_section_sign = 0
        running_balance = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect Section Headers
            if "DEPOSITS" in line.upper() or "CREDITS" in line.upper():
                current_section_sign = 1
            elif "DEBITS" in line.upper() or "WITHDRAWALS" in line.upper():
                current_section_sign = -1

            # Check for Beginning Balance
            if "BEGINNING BALANCE" in line.upper():
                tokens = money_pattern.findall(line)
                if tokens:
                    # Assume the last number is the balance
                    running_balance = self._clean_money(tokens[-1])
                continue # Skip row

            if "ENDING BALANCE" in line.upper():
                continue

            match_date = date_pattern.match(line)
            if match_date:
                date_str = match_date.group(1)

                # Extract all money tokens in the line
                money_tokens = money_pattern.findall(line)

                raw_amount = 0.0
                balance = None
                desc_str = ""

                if not money_tokens:
                    # No money found, treat as continuation or invalid
                    if data and not "Balance" in line:
                         data[-1]['Description'] += " " + line
                    continue

                # Determine Format: Date Amount Desc (Format 1) vs Date Desc Amount [Bal] (Format 2)
                # Check position of first token
                first_token = money_tokens[0]
                content_part = line[len(date_str):]
                idx_first = content_part.find(first_token)
                prefix = content_part[:idx_first].strip()

                # If prefix is empty (only spaces), it's Format 1 (Date Amount ...)
                is_format_1 = (len(prefix) == 0)

                if is_format_1:
                    # Format 1: Date Amount Desc
                    amt_str = first_token
                    raw_amount = abs(self._clean_money(amt_str))
                    # Description is everything after the amount
                    desc_str = content_part[idx_first + len(first_token):].strip()
                    # Balance usually not present or ignored in this legacy format
                    balance = None
                else:
                    # Format 2: Date Desc Amount [Balance]
                    if len(money_tokens) >= 2:
                        bal_str = money_tokens[-1]
                        amt_str = money_tokens[-2]
                        balance = self._clean_money(bal_str)
                        raw_amount = abs(self._clean_money(amt_str))
                        # Description: Remove last 2 tokens
                        tokens_to_remove = money_tokens[-2:]
                    else:
                        amt_str = money_tokens[-1]
                        raw_amount = abs(self._clean_money(amt_str))
                        balance = None
                        tokens_to_remove = money_tokens[-1:]

                    # Determine Description
                    temp_line = content_part.strip()
                    for tok in reversed(tokens_to_remove):
                         idx = temp_line.rfind(tok)
                         if idx != -1:
                             temp_line = temp_line[:idx]
                    desc_str = temp_line.strip()

                # Determine Sign
                final_amount = raw_amount
                sign_determined = False

                # Method 1: Balance Math (Only applies if we found a Balance)
                if running_balance is not None and balance is not None:
                    delta = balance - running_balance
                    # Tolerance for float comparison
                    if abs(abs(delta) - raw_amount) < 0.02:
                        final_amount = delta # Capture sign from delta
                        sign_determined = True
                        running_balance = balance # Update

                if not sign_determined:
                    # Method 2: Keywords/Section
                    desc_upper = desc_str.upper()
                    sign = current_section_sign

                    if "DEBIT" in desc_upper and "CREDIT" not in desc_upper:
                        sign = -1
                    elif "CREDIT" in desc_upper and "DEBIT" not in desc_upper:
                        sign = 1
                    elif "WITHDRAWAL" in desc_upper:
                        sign = -1
                    elif "DEP" in desc_upper or "DEPOSIT" in desc_upper:
                        sign = 1
                    elif "PAYMENT" in desc_upper:
                         sign = -1

                    if sign != 0:
                        final_amount = raw_amount * sign

                    # If we have a balance but math didn't match, we still update running balance
                    # for the next row (trusting the statement's balance column)
                    if balance is not None:
                        running_balance = balance

                data.append({
                    'Date': date_str,
                    'Amount': final_amount,
                    'Description': desc_str
                })

            else:
                 # Continuation line
                 # Avoid appending if it looks like a header or garbage
                 if data and "Transactions" not in line and "Balance" not in line:
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
