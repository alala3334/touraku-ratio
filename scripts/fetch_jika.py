#!/usr/bin/env python3
"""東証の市場別時価総額（月末）を JPX から取得し、data/ に蓄積する。

元データ: https://www.jpx.co.jp/markets/statistics-equities/misc/02.html の
「市場別時価総額」Excel（historical-jika.xlsx）。毎月第1営業日の13時以降に前月末分が載る。
2022年4月以降はプライム市場、それより前は市場第一部の時価総額を prime 列に入れる（market 列で区別）。
total は東証全体（内国株式）の合計。単位はどちらも億円。2009年1月以降を保存する。

Excel を読むのに openpyxl を使う（pip install openpyxl）。
"""
import csv
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl

PAGE = "https://www.jpx.co.jp/markets/statistics-equities/misc/02.html"
START = "2009-01-01"
UA = "Mozilla/5.0 (touraku-ratio recorder)"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "jika.csv"
JSON_PATH = ROOT / "data" / "jika.json"
FIELDS = ["date", "prime", "total", "market"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch():
    # Excel の置き場所（URL の途中）は更新で変わることがあるので、ページからリンクを探す
    html = get(PAGE).decode("utf-8", "replace")
    m = re.search(r'href="([^"]*historical-jika\.xlsx)"', html)
    if not m:
        raise RuntimeError("市場別時価総額の Excel へのリンクが見つかりません")
    wb = openpyxl.load_workbook(io.BytesIO(get(urllib.parse.urljoin(PAGE, m.group(1)))), data_only=True)
    out = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        head = next((i for i, r in enumerate(rows) if r and isinstance(r[0], str) and r[0].startswith("月末")), None)
        if head is None:
            continue
        labels = [str(c or "") for c in rows[head]]
        # 新しいシートは「プライム」、旧シートは「一部」が先頭の市場。合計は「合計」の列
        if any(l.startswith("プライム") for l in labels):
            first, market = next(i for i, l in enumerate(labels) if l.startswith("プライム")), "prime"
        elif any(l.startswith("一部") for l in labels):
            first, market = next(i for i, l in enumerate(labels) if l.startswith("一部")), "first"
        else:
            continue
        total = next(i for i, l in enumerate(labels) if l.startswith("合計"))
        for r in rows[head + 1:]:
            if not isinstance(r[0], datetime) or not isinstance(r[first], (int, float)):
                continue
            date = r[0].date().isoformat()
            if date < START:
                continue
            # 百万円 → 億円
            out[date] = {"prime": round(r[first] / 100), "total": round(r[total] / 100), "market": market}
    if not out:
        raise RuntimeError("時価総額のデータが読み取れませんでした")
    return out


def load():
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="") as f:
        return {r["date"]: {"prime": int(r["prime"]), "total": int(r["total"]), "market": r["market"]} for r in csv.DictReader(f)}


def save(data):
    dates = sorted(data)
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for d in dates:
            w.writerow([d, *(data[d][k] for k in FIELDS[1:])])
    payload = {
        "source": PAGE,
        "updated": datetime.now(JST).isoformat(timespec="minutes"),
        "fields": FIELDS,
        "rows": [[d, *(data[d][k] for k in FIELDS[1:])] for d in dates],
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    data = load()
    before = len(data)
    data.update(fetch())
    save(data)
    last = max(data)
    print(f"{len(data)} カ月分 (+{len(data) - before})  最新 {last}  プライム={data[last]['prime']:,}億円  東証全体={data[last]['total']:,}億円")


if __name__ == "__main__":
    sys.exit(main())
