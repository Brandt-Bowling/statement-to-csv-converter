with open("statement_parser.py", "r") as f:
    content = f.read()

# We need to rewrite parse_loan_balance to be more robust
import re

def rewrite_parse_loan_balance(content):
    # Find the def parse_loan_balance block
    start_idx = content.find("    def parse_loan_balance(self, pdf_file) -> pd.DataFrame:")
    if start_idx == -1:
        return content

    end_idx = content.find("    def _extract_text_with_ocr", start_idx)
    if end_idx == -1:
        end_idx = len(content)

    new_method = """    def parse_loan_balance(self, pdf_file) -> pd.DataFrame:
        \"\"\"
        Extracts Statement Date and Outstanding Balance from the PDF.
        Returns a DataFrame with columns: ['Date', 'Balance']
        \"\"\"
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)

        all_text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\\n"
        except Exception as e:
            print(f"Error reading PDF with pdfplumber: {e}")

        def extract_date_and_bal(text):
            match_date = re.search(r"(?:Statement\\s+Date|Date)\\s*[:]?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})", text, re.IGNORECASE)
            if not match_date:
                match_date = re.search(r"(?:Statement\\s+Date|Date)[\\s:]*\\n[\\s]*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})", text, re.IGNORECASE)

            date = match_date.group(1) if match_date else None

            # Look for outstanding balance. Use a generous pattern to skip garbage between 'principal' and the amount.
            # Also handle possible OCR artifacts like spaces in $ or missing $.
            regex = r"outstanding\\s+(?:balance|principal).*?(?P<amt>\\$?\\s*[0-9]{1,3}(?:,[0-9]{3})+(?:\\.\\d{2})?|\\$?\\s*[0-9]+\\.\\d{2}(?!\\d|\\s*%))"
            match_bal = re.search(regex, text, re.IGNORECASE | re.DOTALL)

            if match_bal:
                val = match_bal.group('amt').replace(',', '').replace('$', '').strip()
                try:
                    balance = -abs(float(val))
                except ValueError:
                    balance = None
            else:
                balance = None

            return date, balance

        date, balance = extract_date_and_bal(all_text)

        # Fallback to OCR if either is missing
        if date is None or balance is None:
            print("Date or balance missing. Attempting OCR fallback...")
            try:
                ocr_text = self._extract_text_with_ocr(pdf_file)
                ocr_date, ocr_balance = extract_date_and_bal(ocr_text)

                if date is None and ocr_date is not None:
                    date = ocr_date
                if balance is None and ocr_balance is not None:
                    balance = ocr_balance
            except Exception as e:
                print(f"Error extracting text with OCR: {e}")

        if date or balance is not None:
            return pd.DataFrame([{'Date': date, 'Balance': balance}])
        else:
            return pd.DataFrame(columns=['Date', 'Balance'])

"""
    return content[:start_idx] + new_method + content[end_idx:]

new_content = rewrite_parse_loan_balance(content)
with open("statement_parser.py", "w") as f:
    f.write(new_content)
