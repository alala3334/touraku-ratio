#!/usr/bin/env python3
"""nikkei225jp.com の日経225 PER・PBR・配当利回りと10年国債利回り（日次）を取得し、data/ に蓄積する。

元データ: https://nikkei225jp.com/data/per.php が読み込む daily2.json（2009年6月〜）。
PER/PBR/配当利回りは「加重平均」(_w) と「指数ベース」(_i) の2種類がある。
取得した行は既存の履歴に日付単位で上書き・追加する。
"""
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = "https://nikkei225jp.com/_data/_nfsDATA/data_DAY/daily2.json"
REFERER = "https://nikkei225jp.com/data/per.php"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "valuation.csv"
JSON_PATH = ROOT / "data" / "valuation.json"
FIELDS = ["date", "nikkei", "per_w", "pbr_w", "div_w", "per_i", "pbr_i", "div_i", "jgb10"]
NUMERIC = FIELDS[1:]
# 元データの列番号: 1=日経225終値 12/13/14=加重平均 PER/PBR/配当利回り 25/26/27=指数ベース 16=10年国債利回り
COLUMNS = {"nikkei": 1, "per_w": 12, "pbr_w": 13, "div_w": 14, "per_i": 25, "pbr_i": 26, "div_i": 27, "jgb10": 16}


def fetch():
    req = urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0 (touraku-ratio recorder)", "Referer": REFERER})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8")
    m = re.search(r"=\s*(\[.*\])\s*;?\s*$", text, re.S)
    if not m:
        raise RuntimeError("DAILY 配列が見つかりません")
    # 空欄 (",,") が混じるので null に置き換えてから JSON として読む
    body = re.sub(r"(?<=[\[,])\s*(?=[,\]])", "null", m.group(1))
    rows = json.loads(body)

    def num(v, key):
        if not isinstance(v, (int, float)):
            return None
        # 国債利回りはマイナス金利の時期があるので 0 以下もそのまま残す。それ以外の 0 は欠損扱い
        return v if key == "jgb10" or v > 0 else None

    out = {}
    for row in rows:
        rec = {k: num(row[i], k) for k, i in COLUMNS.items()}
        if rec["nikkei"] is None:
            continue
        date = datetime.fromtimestamp(row[0] / 1000, JST).date().isoformat()
        out[date] = {"date": date, **rec}
    return out


def load():
    if not CSV_PATH.exists():
        return {}
    data = {}
    with CSV_PATH.open(newline="") as f:
        for r in csv.DictReader(f):
            data[r["date"]] = {"date": r["date"], **{k: float(r[k]) if r[k] else None for k in NUMERIC}}
    return data


def merge(old, new):
    # 空欄で既存値を消さない
    merged = dict(old)
    for date, rec in new.items():
        prev = merged.get(date, {})
        merged[date] = {k: (v if v is not None else prev.get(k)) for k, v in rec.items()}
    return merged


def save(records):
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in records:
            w.writerow({k: ("" if r.get(k) is None else r[k]) for k in FIELDS})
    payload = {
        "source": REFERER,
        "updated": datetime.now(JST).isoformat(timespec="minutes"),
        "fields": FIELDS,
        "rows": [[r.get(k) for k in FIELDS] for r in records],
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    data = load()
    before = len(data)
    data = merge(data, fetch())
    records = sorted(data.values(), key=lambda r: r["date"])
    save(records)
    last = records[-1]
    print(f"{len(records)} 日分 (+{len(records) - before})  最新 {last['date']}  PER={last['per_w']}/{last['per_i']}"
          f" PBR={last['pbr_w']}/{last['pbr_i']} 10年債={last['jgb10']}%  (加重平均/指数ベース)")


if __name__ == "__main__":
    sys.exit(main())
