#!/usr/bin/env python3
"""米国債の利回り（3カ月・2年・5年・10年・30年、日次）と景気後退期を FRED から取得し、data/ に蓄積する。

逆イールド（短期金利が長期金利を上回る状態）とイールドカーブを見るためのデータ。
元データ: セントルイス連銀 FRED の DGS3MO / DGS2 / DGS5 / DGS10 / DGS30（%）、
景気後退期は USREC（全米経済研究所 NBER の判定、月次で 1=景気後退）。
1990年以降を保存し、取得した行は日付単位で上書き・追加する。
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={start}"
SOURCE_PAGE = "https://fred.stlouisfed.org/categories/115"
START = "1990-01-01"
# FRED はブラウザ風の User-Agent だと応答しないことがあるので、ツール名を名乗る
UA = "touraku-ratio-recorder/1.0 (+https://github.com/alala3334/touraku-ratio)"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "yield.csv"
JSON_PATH = ROOT / "data" / "yield.json"
# 列名 → FRED の系列 ID
SERIES = {"y3m": "DGS3MO", "y2": "DGS2", "y5": "DGS5", "y10": "DGS10", "y30": "DGS30"}
FIELDS = ["date", *SERIES]


def fetch_series(series_id):
    req = urllib.request.Request(BASE.format(id=series_id, start=START), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8")
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        date, value = row["observation_date"], row[series_id]
        # 休場日は "." や空欄になっている
        if date < START or value in ("", "."):
            continue
        out[date] = float(value)
    if not out:
        raise RuntimeError(f"{series_id} のデータが取得できませんでした")
    return out


def fetch_recessions():
    """USREC（月次）から、景気後退期を [開始月の初日, 終了月の末日] の組で返す。"""
    months = fetch_series("USREC")
    spans, start = [], None
    for month in sorted(months):
        if months[month] == 1 and start is None:
            start = month
        elif months[month] == 0 and start is not None:
            spans.append([start, (datetime.fromisoformat(month) - timedelta(days=1)).date().isoformat()])
            start = None
    if start is not None:  # まだ景気後退が続いている
        spans.append([start, None])
    return spans


def load():
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="") as f:
        return {r["date"]: {k: float(r[k]) for k in SERIES if r[k]} for r in csv.DictReader(f)}


def save(data, recessions):
    dates = sorted(data)
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for d in dates:
            w.writerow([d, *(data[d].get(k, "") for k in SERIES)])
    payload = {
        "source": SOURCE_PAGE,
        "updated": datetime.now(JST).isoformat(timespec="minutes"),
        "fields": FIELDS,
        "rows": [[d, *(data[d].get(k) for k in SERIES)] for d in dates],
        "recessions": recessions,
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    data = load()
    before = len(data)
    for key, series_id in SERIES.items():
        for date, value in fetch_series(series_id).items():
            data.setdefault(date, {})[key] = value
    save(data, fetch_recessions())
    last = max(data)
    r = data[last]
    print(f"{len(data)} 日分 (+{len(data) - before})  最新 {last}  " + " ".join(f"{k}={v}" for k, v in r.items()))


if __name__ == "__main__":
    sys.exit(main())
