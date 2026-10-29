import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fapiao_ledger.parser import parse_invoice_text, parse_invoice_xml, scan_folder
from fapiao_ledger.cli import build_new_name

SAMPLE_TEXT = """
电子发票（普通发票）
发票号码：25312000000012345678
开票日期：2025年09月03日
购买方 名称：广州鹿用信息服务有限公司
销售方 名称：深圳市云杉科技有限公司
合计 ¥943.40 ¥56.60
价税合计（大写）壹仟元整 （小写）¥1,000.00
"""


class TestTextParser(unittest.TestCase):
    def test_fields(self):
        inv = parse_invoice_text(SAMPLE_TEXT, "a.pdf")
        self.assertEqual(inv.invoice_no, "25312000000012345678")
        self.assertEqual(inv.date, "2025-09-03")
        self.assertEqual(inv.seller, "深圳市云杉科技有限公司")
        self.assertEqual(inv.buyer, "广州鹿用信息服务有限公司")
        self.assertEqual(inv.amount_total, 1000.00)
        self.assertEqual(inv.amount_excl, 943.40)
        self.assertEqual(inv.tax, 56.60)
        self.assertTrue(inv.parse_ok)

    def test_new_name(self):
        inv = parse_invoice_text(SAMPLE_TEXT, "a.pdf")
        name = build_new_name(inv, "{date}_{seller}_{amount}_{invoice_no}", ".pdf")
        self.assertEqual(name, "2025-09-03_深圳市云杉科技有限公司_1000.00_25312000000012345678.pdf")


class TestXmlAndDedupe(unittest.TestCase):
    XML = """<?xml version="1.0" encoding="UTF-8"?>
<EInvoice><InvoiceNumber>25312000000012345678</InvoiceNumber>
<IssueTime>2025-09-03</IssueTime><SellerName>深圳市云杉科技有限公司</SellerName>
<BuyerName>广州鹿用信息服务有限公司</BuyerName>
<TotalTaxIncludedAmount>1000.00</TotalTaxIncludedAmount></EInvoice>"""

    def test_xml_and_duplicate_flag(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "x1.xml").write_text(self.XML, encoding="utf-8")
            (p / "x2.xml").write_text(self.XML, encoding="utf-8")
            inv = parse_invoice_xml(p / "x1.xml")
            self.assertEqual(inv.amount_total, 1000.00)
            self.assertTrue(inv.parse_ok)
            invoices = scan_folder(p)
            self.assertTrue(all(i.is_duplicate for i in invoices))


if __name__ == "__main__":
    unittest.main()
