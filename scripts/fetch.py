#!/usr/bin/env python3
"""nikkei225jp.com の騰落データを取得し、data/ に蓄積する。

元データ: https://nikkei225jp.com/data/touraku.php が読み込む daily2year.json
（直近約2年分）。取得した行は既存の履歴に日付単位で上書き・追加するので、
毎日実行すれば2年より前のデータも残り続ける。
"""
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = "https://nikkei225jp.com/_data/_nfsDATA/data_DAY/daily2year.json"
REFERER = "https://nikkei225jp.com/data/touraku.php"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "touraku.csv"
JSON_PATH = ROOT / "data" / "touraku.json"
PERIODS = (25, 15, 10, 6)
FIELDS = ["date", "nikkei", "volume", "advances", "declines", "official25"] + [f"r{p}" for p in PERIODS]


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

    def num(v):
        return v if isinstance(v, (int, float)) and v > 0 else None

    out = {}
    for row in rows:
        # 列: 0=日時(ms) 1=日経225終値 2=プライム出来高(百万株) 5=値上がり 6=値下がり 7=騰落レシオ25日(公式)
        date = datetime.fromtimestamp(row[0] / 1000, JST).date().isoformat()
        up, dn = num(row[5]), num(row[6])
        if up is None or dn is None:
            continue
        out[date] = {
            "date": date,
            "nikkei": num(row[1]),
            "volume": num(row[2]),
            "advances": int(up),
            "declines": int(dn),
            "official25": num(row[7]),
        }
    return out


def load():
    if not CSV_PATH.exists():
        return {}
    data = {}
    with CSV_PATH.open(newline="") as f:
        for r in csv.DictReader(f):
            rec = {"date": r["date"]}
            for k in ("nikkei", "volume", "official25"):
                rec[k] = float(r[k]) if r.get(k) else None
            rec["advances"] = int(r["advances"])
            rec["declines"] = int(r["declines"])
            data[r["date"]] = rec
    return data


def compute(records):
    for i, rec in enumerate(records):
        for p in PERIODS:
            if i + 1 < p:
                rec[f"r{p}"] = None
                continue
            win = records[i + 1 - p : i + 1]
            dn = sum(r["declines"] for r in win)
            rec[f"r{p}"] = round(sum(r["advances"] for r in win) / dn * 100, 2) if dn else None


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
    data.update(fetch())
    records = sorted(data.values(), key=lambda r: r["date"])
    compute(records)
    save(records)
    last = records[-1]
    print(f"{len(records)} 日分 (+{len(records) - before})  最新 {last['date']}  25日={last['r25']} (公式 {last['official25']})")


if __name__ == "__main__":
    sys.exit(main())
