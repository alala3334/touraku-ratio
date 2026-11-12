#!/usr/bin/env python3
"""米国10年国債利回り（日次）を FRED から取得し、data/ に蓄積する。

元データ: セントルイス連銀 FRED の DGS10（米国債10年物 利回り、%）。
日付は米国の営業日。2009年6月以降を保存し、取得した行は日付単位で上書き・追加する。
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
SOURCE_PAGE = "https://fred.stlouisfed.org/series/DGS10"
START = "2009-06-01"
# FRED はブラウザ風の User-Agent だと応答しないことがあるので、ツール名を名乗る
UA = "touraku-ratio-recorder/1.0 (+https://github.com/alala3334/touraku-ratio)"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "us10y.csv"
JSON_PATH = ROOT / "data" / "us10y.json"
FIELDS = ["date", "us10y"]


def fetch():
    req = urllib.request.Request(SRC, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8")
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        date, value = row["observation_date"], row["DGS10"]
        # 休場日は "." や空欄になっている
        if date < START or value in ("", "."):
            continue
        out[date] = float(value)
    if not out:
        raise RuntimeError("DGS10 のデータが取得できませんでした")
    return out


def load():
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="") as f:
        return {r["date"]: float(r["us10y"]) for r in csv.DictReader(f)}


def save(data):
    dates = sorted(data)
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for d in dates:
            w.writerow([d, data[d]])
    payload = {
        "source": SOURCE_PAGE,
        "updated": datetime.now(JST).isoformat(timespec="minutes"),
        "fields": FIELDS,
        "rows": [[d, data[d]] for d in dates],
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    data = load()
    before = len(data)
    data.update(fetch())
    save(data)
    last = max(data)
    print(f"{len(data)} 日分 (+{len(data) - before})  最新 {last}  米10年債={data[last]}%")


if __name__ == "__main__":
    sys.exit(main())
