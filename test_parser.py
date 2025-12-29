import unittest
import pandas as pd
from statement_parser import BankStatementParser
import os

class TestBankStatementParser(unittest.TestCase):
    def test_parse_mock_pdf(self):
        filename = "test_statement.pdf"
        self.assertTrue(os.path.exists(filename), "Test PDF does not exist")

        parser = BankStatementParser()
        df = parser.parse(filename)

        # Check if DataFrame is returned
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "DataFrame should not be empty")

        # Check Columns
        expected_cols = ["Account", "Date", "Amount"]
        for col in expected_cols:
            self.assertIn(col, df.columns)

        # Check Account Number extraction
        self.assertEqual(df['Account'].iloc[0], "123456789")

        # Check Data Content
        # We expect 5 rows
        self.assertEqual(len(df), 5)

        # Check specific row
        # Date: 01/05/2023, Amount: -50.25
        row = df[df['Date'] == "01/05/2023"].iloc[0]
        self.assertEqual(row['Amount'], -50.25)

        print("\nParsed Data:")
        print(df)

if __name__ == '__main__':
    unittest.main()
