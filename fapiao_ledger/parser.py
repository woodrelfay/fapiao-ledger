"""发票解析：从 PDF 文字层 / XML 数电票 / OFD 中抽取关键字段。

设计原则：纯本地解析，不联网、不上传。解析分两层——
1) extract_* 负责把文件变成文本或字段字典；
2) parse_invoice_text 负责用正则从文本里抽字段，方便单测和扩展。
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class Invoice:
    source_file: str
    invoice_no: str = ""
    date: str = ""            # YYYY-MM-DD
    seller: str = ""
    buyer: str = ""
    amount_excl: float | None = None   # 不含税金额
    tax: float | None = None           # 税额
    amount_total: float | None = None  # 价税合计
    invoice_type: str = ""
    is_duplicate: bool = False
    parse_ok: bool = False
    note: str = ""

    @property
    def month(self) -> str:
        return self.date[:7] if len(self.date) >= 7 else "未知月份"


def _money(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return round(float(s.replace(",", "").replace("¥", "").replace("￥", "").strip()), 2)
    except ValueError:
        return None


def _norm_date(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"(\d{4})(\d{2})(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return raw


def parse_invoice_text(text: str, source_file: str = "") -> Invoice:
    """从发票文字层文本中抽取字段（PDF/OFD 通用）。"""
    inv = Invoice(source_file=source_file)
    t = re.sub(r"[ \t]+", " ", text)

    m = re.search(r"发票号码[:：]?\s*(\d{8,20})", t)
    if m:
        inv.invoice_no = m.group(1)

    m = re.search(r"开票日期[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日|\d{4}[-/]\d{1,2}[-/]\d{1,2})", t)
    if m:
        inv.date = _norm_date(m.group(1))

    # 增值税发票版式：购买方在上、销售方在下，两处「名称：」
    names = re.findall(r"名\s*称[:：]\s*([^\n\r：:]{2,50})", t)
    names = [n.strip() for n in names if n.strip()]
    if len(names) >= 2:
        inv.buyer, inv.seller = names[0], names[1]
    elif len(names) == 1:
        inv.buyer = names[0]
    m = re.search(r"销售方[^名]{0,10}名\s*称[:：]\s*([^\n\r]{2,50})", t)
    if m:
        inv.seller = m.group(1).strip()
    m = re.search(r"购买方[^名]{0,10}名\s*称[:：]\s*([^\n\r]{2,50})", t)
    if m:
        inv.buyer = m.group(1).strip()

    # 价税合计：优先取「（小写）¥x,xxx.xx」
    m = re.search(r"价税合计[^¥￥\d]{0,30}[¥￥]\s*([\d,]+\.\d{2})", t)
    if not m:
        m = re.search(r"价税合计[\s\S]{0,40}?([\d,]+\.\d{2})", t)
    if m:
        inv.amount_total = _money(m.group(1))

    # 合计行：金额（不含税）与税额通常同行出现两个金额
    m = re.search(r"合\s*计\s*[¥￥]\s*([\d,]+\.\d{2})\s*[¥￥]\s*([\d,]+\.\d{2})", t)
    if m:
        inv.amount_excl = _money(m.group(1))
        inv.tax = _money(m.group(2))
    if inv.amount_excl is None and inv.amount_total is not None and inv.tax is not None:
        inv.amount_excl = round(inv.amount_total - inv.tax, 2)

    if "数电" in t or "全电" in t:
        inv.invoice_type = "数电票"
    elif "增值税专用发票" in t:
        inv.invoice_type = "增值税专用发票"
    elif "增值税普通发票" in t:
        inv.invoice_type = "增值税普通发票"

    inv.parse_ok = bool(inv.invoice_no and inv.date)
    if not inv.parse_ok:
        inv.note = "关键字段缺失，请人工核对"
    return inv


# ---------- XML 数电票 ----------

_XML_KEYS = {
    "invoice_no": ("invoicenumber", "invoicecodeandnumber", "fphm", "发票号码"),
    "date": ("issuetime", "issuedate", "invoicedate", "kprq", "开票日期"),
    "seller": ("sellername", "salename", "xfmc", "销售方名称"),
    "buyer": ("buyername", "purchasername", "gfmc", "购买方名称"),
    "amount_total": ("totaltaxincludedamount", "taxincludedamount", "totalamount", "jshj", "价税合计"),
    "amount_excl": ("totalexcludedtaxamount", "excludedtaxamount", "hjje", "金额"),
    "tax": ("totaltaxamount", "hjse", "税额"),
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].strip().lower()


def parse_invoice_xml(path: Path) -> Invoice:
    inv = Invoice(source_file=path.name)
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return parse_invoice_text(path.read_text(encoding="utf-8", errors="ignore"), path.name)
    fields: dict[str, str] = {}
    for el in tree.iter():
        key = _local(el.tag)
        if el.text and el.text.strip() and key not in fields:
            fields[key] = el.text.strip()
        # 中文标签名也收
        raw = el.tag.rsplit("}", 1)[-1].strip()
        if el.text and el.text.strip() and raw not in fields:
            fields[raw] = el.text.strip()

    def pick(kind: str) -> str:
        for k in _XML_KEYS[kind]:
            if k in fields and fields[k]:
                return fields[k]
        return ""

    inv.invoice_no = pick("invoice_no")
    inv.date = _norm_date(pick("date")) if pick("date") else ""
    inv.seller = pick("seller")
    inv.buyer = pick("buyer")
    inv.amount_total = _money(pick("amount_total"))
    inv.amount_excl = _money(pick("amount_excl"))
    inv.tax = _money(pick("tax"))
    inv.invoice_type = "数电票(XML)"
    inv.parse_ok = bool(inv.invoice_no and inv.date)
    if not inv.parse_ok:
        inv.note = "XML 关键字段缺失，请人工核对"
    return inv


# ---------- OFD ----------

def parse_invoice_ofd(path: Path) -> Invoice:
    texts: list[str] = []
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.lower().endswith(".xml"):
                    texts.append(z.read(name).decode("utf-8", errors="ignore"))
    except zipfile.BadZipFile:
        inv = Invoice(source_file=path.name, note="OFD 文件损坏")
        return inv
    blob = "\n".join(texts)
    # OFD 里文字常在 TextCode 节点中，拼起来再走文本解析
    codes = re.findall(r"<(?:\w+:)?TextCode[^>]*>([^<]+)</(?:\w+:)?TextCode>", blob)
    text = " ".join(codes) if codes else re.sub(r"<[^>]+>", " ", blob)
    inv = parse_invoice_text(text, path.name)
    inv.invoice_type = inv.invoice_type or "数电票(OFD)"
    return inv


# ---------- PDF ----------

def extract_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except ImportError:
        return ""


def parse_invoice_file(path: Path) -> Invoice:
    suffix = path.suffix.lower()
    if suffix == ".xml":
        return parse_invoice_xml(path)
    if suffix == ".ofd":
        return parse_invoice_ofd(path)
    if suffix == ".pdf":
        text = extract_pdf_text(path)
        if not text.strip():
            inv = Invoice(source_file=path.name,
                          note="PDF 无文字层（可能是扫描件），需 OCR，暂未解析")
            return inv
        return parse_invoice_text(text, path.name)
    return Invoice(source_file=path.name, note=f"不支持的格式 {suffix}")


SUPPORTED = {".pdf", ".xml", ".ofd"}


def scan_folder(folder: Path) -> list[Invoice]:
    files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED and p.is_file())
    invoices = [parse_invoice_file(p) for p in files]
    seen: dict[str, int] = {}
    for inv in invoices:
        if inv.invoice_no:
            seen[inv.invoice_no] = seen.get(inv.invoice_no, 0) + 1
    for inv in invoices:
        if inv.invoice_no and seen.get(inv.invoice_no, 0) > 1:
            inv.is_duplicate = True
            inv.note = (inv.note + "；" if inv.note else "") + "重复发票（发票号相同）"
    return invoices
