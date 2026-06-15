import unittest
import pandas as pd
from statement_parser import BankStatementParser
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

class MockPdfFile:
    def __init__(self, content):
        self.content = content
        self.seek_called = False

    def seek(self, pos):
        self.seek_called = True

class TestLoanBalanceParser(unittest.TestCase):
    def setUp(self):
        self.parser = BankStatementParser()
        self.test_pdf = "test_loan_statement.pdf"

        # Generate a mock PDF for loan balance
        doc = SimpleDocTemplate(self.test_pdf, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Mortgage Statement", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Account Number: 123456789", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Statement Date: 05/12/2023", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("outstanding principal     $298,000.50", styles['Normal']))

        doc.build(elements)

    def tearDown(self):
        if os.path.exists(self.test_pdf):
            os.remove(self.test_pdf)

    def test_parse_loan_balance_from_pdf(self):
        df = self.parser.parse_loan_balance(self.test_pdf)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

        self.assertIn('Date', df.columns)
        self.assertIn('Balance', df.columns)

        self.assertEqual(df['Date'].iloc[0], '05/12/2023')
        self.assertEqual(df['Balance'].iloc[0], -298000.50)

if __name__ == '__main__':
    unittest.main()
