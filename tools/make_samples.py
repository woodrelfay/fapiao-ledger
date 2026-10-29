"""生成脱敏样例发票（虚构公司/号码），用于演示和测试。

用法：python tools/make_samples.py [输出目录]   默认 samples/
生成：4 个 XML 数电票（含 1 张重复）+ 3 个带文字层的 PDF 发票（乱文件名，模拟真实场景）。
PDF 生成依赖 pymupdf（仅本工具需要，运行时解析不依赖它）。
"""
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "samples"

INVOICES = [
    dict(no="25312000000012345678", date="2025-09-03", seller="深圳市云杉科技有限公司",
         buyer="广州鹿用信息服务有限公司", excl=943.40, tax=56.60, total=1000.00),
    dict(no="25312000000012345679", date="2025-09-18", seller="北京星桥餐饮管理有限公司",
         buyer="广州鹿用信息服务有限公司", excl=320.75, tax=19.25, total=340.00),
    dict(no="25312000000012345680", date="2025-10-07", seller="上海墨池文化传播有限公司",
         buyer="广州鹿用信息服务有限公司", excl=2264.15, tax=135.85, total=2400.00),
]

XML_TMPL = """<?xml version="1.0" encoding="UTF-8"?>
<EInvoice>
  <Header><InvoiceNumber>{no}</InvoiceNumber><IssueTime>{date}</IssueTime></Header>
  <SellerInformation><SellerName>{seller}</SellerName></SellerInformation>
  <BuyerInformation><BuyerName>{buyer}</BuyerName></BuyerInformation>
  <TotalInformation>
    <TotalExcludedTaxAmount>{excl:.2f}</TotalExcludedTaxAmount>
    <TotalTaxAmount>{tax:.2f}</TotalTaxAmount>
    <TotalTaxIncludedAmount>{total:.2f}</TotalTaxIncludedAmount>
  </TotalInformation>
</EInvoice>
"""


def make_xmls(out: Path) -> None:
    d = out / "xml"
    d.mkdir(parents=True, exist_ok=True)
    messy = ["dzfp_2531_下载1.xml", "发票-9月办公.xml", "餐饮发票.xml", "dzfp_2510_设计费.xml"]
    items = INVOICES + [INVOICES[0]]  # 最后一张与第一张同号 = 重复发票
    for name, inv in zip(messy, items):
        (d / name).write_text(XML_TMPL.format(**inv), encoding="utf-8")
    print(f"XML 样例 → {d}（{len(items)} 个，含 1 张重复）")


# 样例金额的大写写法（仅三张虚构样例用到）
_RMB_UPPER = {1000.00: "壹仟元整", 340.00: "叁佰肆拾元整", 2400.00: "贰仟肆佰元整"}


def make_pdfs(out: Path) -> None:
    """用 PyMuPDF 内置 CJK 字体 china-s 生成带文字层的 PDF。

    不用 reportlab+系统 TTC 字体：Noto CJK 的 TTC 是 PostScript 轮廓，
    reportlab 注册会报 "postscript outlines are not supported"。
    PyMuPDF 的 china-s 是内置简体中文字体，无需任何外部字体文件，
    且生成的文字可被 pdfplumber 正常抽取。
    """
    try:
        import pymupdf as fitz  # 新版导入名；旧版包名 fitz 已弃用
    except ImportError:
        try:
            import fitz
        except ImportError:
            print("未安装 pymupdf，跳过 PDF 样例（pip install pymupdf）")
            return
    d = out / "pdf"
    d.mkdir(parents=True, exist_ok=True)
    messy = ["扫描件_001.pdf", "微信图片发票.pdf", "10月差旅.pdf"]
    for name, inv in zip(messy, INVOICES):
        lines = [
            "电子发票（普通发票）",
            f"发票号码：{inv['no']}",
            f"开票日期：{inv['date'][:4]}年{int(inv['date'][5:7]):02d}月{int(inv['date'][8:]):02d}日",
            "购买方",
            f"名称：{inv['buyer']}",
            "销售方",
            f"名称：{inv['seller']}",
            f"合计 ¥{inv['excl']:.2f} ¥{inv['tax']:.2f}",
            f"价税合计（大写）{_RMB_UPPER.get(inv['total'], '')} （小写）¥{inv['total']:,.2f}",
        ]
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4
        y = 70
        for line in lines:
            page.insert_text(fitz.Point(60, y), line, fontsize=13, fontname="china-s")
            y += 32
        doc.save(d / name)
        doc.close()
    print(f"PDF 样例 → {d}（{len(messy)} 个）")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_xmls(OUT)
    make_pdfs(OUT)
