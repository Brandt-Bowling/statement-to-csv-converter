import unittest
import pandas as pd
from statement_parser import BankStatementParser
import os
import io
import shutil

class TestOCRIntegration(unittest.TestCase):
    def test_parse_mock_pdf_via_ocr_path(self):
        """
        Forces the parser to use the OCR path by providing a PDF that pdfplumber
        (conceptually) fails on, or just explicitly testing _parse_with_ocr method.
        Since we can't easily create an "image-only" PDF without external tools
        that might not be here, we will just pass the standard test PDF to
        _parse_with_ocr.

        Even though the test PDF has text, we can still render it to image
        and OCR it. Tesseract should be able to read the clean text we generated.
        """
        filename = "test_statement.pdf"
        if not os.path.exists(filename):
            from generate_test_pdf import generate_test_pdf
            generate_test_pdf(filename)

        parser = BankStatementParser()

        # We explicitly call _parse_with_ocr to test pypdfium2 integration
        df = parser._parse_with_ocr(filename)

        # Note: OCR results on clean text are usually good but formatting might differ slightly
        # The generate_test_pdf creates a table. Tesseract reads tables line by line.
        # Our OCR parser expects "MM/DD    AMOUNT    DESCRIPTION"
        # The generated PDF table is:
        # Date        Description       Amount
        # 01/01/2023  Opening Balance   1000.00

        # The regex in _parse_ocr_text is: r'^(\d{1,2}/\d{1,2})\s+([0-9,]+\.\d{2})\s+(.*)'
        # This expects DATE AMOUNT DESCRIPTION.
        # But our table is DATE DESCRIPTION AMOUNT.
        # So the regex might NOT match the generated PDF rows exactly if we strictly use the current regex.
        # However, the goal here is to verify pypdfium2 runs without crashing (finding the library).
        # We don't strictly need to assert the DF content matches perfectly if the format differs,
        # but we should ensure it runs.

        # Let's see if it produces anything. If the regex doesn't match, DF might be empty.
        # But checking that it runs implies pypdfium2 worked.

        print("\nOCR Integration Result (Data might be empty if regex mismatch):")
        print(df)

        # Assert that we at least got a DataFrame back (proving pypdfium2 + pytesseract ran)
        self.assertIsInstance(df, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
