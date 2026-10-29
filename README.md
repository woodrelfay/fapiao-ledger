# fapiao-ledger 发票台账助手

> 一堆乱名的电子发票，一条命令整理成台账：批量重命名、按发票号查重、按月份分类、导出 Excel。**纯本地运行，不上传任何文件。**

报销和记账时最烦的体力活：`dzfp_下载1.pdf`、`微信图片发票.pdf`、`扫描件_001.pdf`……要一张张打开看金额、改文件名、再手工往 Excel 里抄，还怕同一张发票交两次。这个工具把这套流程一次做完。

## 效果

```
$ python -m fapiao_ledger samples
共扫描 7 张发票
  10月差旅.pdf        →  2025-10-07_上海墨池文化传播有限公司_2400.00_25312000000012345680.pdf
  微信图片发票.pdf     →  2025-09-18_北京星桥餐饮管理有限公司_340.00_25312000000012345679.pdf
  扫描件_001.pdf       →  2025-09-03_深圳市云杉科技有限公司_1000.00_25312000000012345678.pdf
  ...
解析成功 7 张｜重复 7 张｜价税合计（不含重复）¥3,740.00
当前是预览模式，没有改动任何文件。确认无误后加 --apply 执行。
台账已导出：samples/发票台账.xlsx
```

（以上为随仓库附带的虚构样例的真实运行输出：7 个文件实际只有 3 个发票号，
同一张票的 PDF 版和 XML 版都在，所以 7 张全部被标记为重复。）

导出的台账里，重复发票整行标红；合计金额按发票号去重，每个号只计一次。

## 快速开始

```bash
pip install -r requirements.txt

# 1) 先预览（默认 dry-run，不动你的文件）
python -m fapiao_ledger /path/to/发票文件夹

# 2) 确认无误，执行改名
python -m fapiao_ledger /path/to/发票文件夹 --apply

# 3) 顺便按月份分文件夹
python -m fapiao_ledger /path/to/发票文件夹 --organize
```

改名记录会写到文件夹里的 `rename_log.csv`，照着它可以把文件名还原回去。

## 支持的格式

| 格式 | 说明 |
|---|---|
| PDF | 读取文字层抽取发票号、日期、销售方/购买方、价税合计、税额；扫描件（无文字层）会单独提示需 OCR |
| XML | 数电票 XML，按标签直接解析，字段最准 |
| OFD | 解包读取内部 XML 后解析 |

抽取字段：开票日期、发票号码、销售方、购买方、不含税金额、税额、价税合计、发票类型。

## 自定义改名模板

```bash
python -m fapiao_ledger ./invoices --pattern "{month}_{seller}_{amount}"
```

可用变量：`{date}` `{month}` `{seller}` `{buyer}` `{amount}` `{invoice_no}`

## 台账导出

默认导出 `发票台账.xlsx`（重复行标红、冻结表头、列宽调好）；也可以 `--export 台账.csv`。

## 演示样例

`samples/` 里有脱敏的虚构样例（公司名和发票号均为编造），可直接拿来试：

```bash
python tools/make_samples.py        # 重新生成样例（PDF 样例需 pip install pymupdf）
python -m fapiao_ledger samples
```

## 测试

```bash
python -m unittest discover -s tests
```

## 路线图

- [ ] 扫描件 OCR（本地模型，不上传）
- [ ] 火车票/机票行程单解析
- [ ] 抬头核对：购买方名称/税号与预设不一致时告警
- [ ] 图形界面（拖拽文件夹版）

## 免责声明

本工具只做文件整理和信息摘录，不做发票真伪查验，台账数据请以税务系统为准。样例数据全部为虚构。

## License

MIT
