import unittest
import pandas as pd
from statement_parser import BankStatementParser

class TestOCRLogic(unittest.TestCase):
    def test_parse_ocr_text(self):
        # Simulated OCR output matching the screenshot provided by user
        ocr_text = """
DEPOSITS AND OTHER CREDITS
DATE..........AMOUNT.TRANSACTION DESCRIPTION
12/08         604.67 ACH CREDIT                   120816
                  CREATING BRIGHTE DIRECT DEP **********7JF3
12/21         198.23 DEPOSIT @ MOBILE
12/22         674.15 ACH CREDIT                   122216
                  CREATING BRIGHTE DIRECT DEP **********7JF3

OTHER DEBITS
DATE..........AMOUNT.TRANSACTION DESCRIPTION
11/28          20.00 ACH DEBIT                    112816
                  VENMO                    PAYMENT          **********9001
11/28         600.00 ACH DEBIT                    112816
                  CITI CARD ONLINE PAYMENT          **********2689
11/29           0.82 DEBIT CARD PURCHASE          112816
                  DOMINO'S 1117            ANN ARBOR       MI
11/29          90.00 ACH DEBIT                    112916
                  CITI CARD ONLINE PAYMENT          **********8009
        """

        parser = BankStatementParser()
        df = parser._parse_text_lines(ocr_text)

        # Verify result
        self.assertFalse(df.empty)
        print(df)

        # Check Transaction 1 (Credit)
        row1 = df.iloc[0]
        self.assertEqual(row1['Date'], '12/08')
        self.assertEqual(row1['Amount'], 604.67) # Positive because section is CREDITS or text says CREDIT
        self.assertIn('ACH CREDIT', row1['Description'])
        self.assertIn('CREATING BRIGHTE', row1['Description']) # Check multi-line append

        # Check Transaction 4 (Debit)
        # 12/08, 12/21, 12/22 -> 3 credits
        # 11/28 20.00 -> 1st debit (index 3)
        row3 = df.iloc[3]
        self.assertEqual(row3['Date'], '11/28')
        self.assertEqual(row3['Amount'], -20.00) # Negative because section is DEBITS

        # Check Transaction 5 (Debit)
        row4 = df.iloc[4]
        self.assertEqual(row4['Date'], '11/28')
        self.assertEqual(row4['Amount'], -600.00)

        # Check total count
        self.assertEqual(len(df), 7)

    def test_parse_digital_text_format(self):
        """
        Tests the new format: Date Description Amount Balance
        """
        text = """
        Transactions
        Date Description Debits Credits Balance
        11/25 ACH DEP 112524 $170.00 $4,919.85
              VENMO CASHOUT
              ************0873
        11/25 ACH WITHDRAWAL 112524 $30.00 $4,889.85
              VENMO PAYMENT
              ************5766
        """
        parser = BankStatementParser()
        df = parser._parse_text_lines(text)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)

        # Row 1: Credit
        row1 = df.iloc[0]
        self.assertEqual(row1['Date'], '11/25')
        self.assertEqual(row1['Amount'], 170.00)
        self.assertIn('VENMO CASHOUT', row1['Description'])

        # Row 2: Debit
        row2 = df.iloc[1]
        self.assertEqual(row2['Date'], '11/25')
        self.assertEqual(row2['Amount'], -30.00)
        self.assertIn('VENMO PAYMENT', row2['Description'])

if __name__ == '__main__':
    unittest.main()
