#!/usr/bin/env python3
"""nikkei225jp.com の裁定買い残・裁定売り残を取得し、data/ に蓄積する。

元データ: https://nikkei225jp.com/data/saitei.php が読み込む daily_saitei.json
（直近約2年分）。金額は週次（週末の日付に入る）、株数は日次。取得した行は
既存の履歴に日付単位で上書き・追加する。
"""
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = "https://nikkei225jp.com/_data/_nfsDATA/json_DAY/daily_saitei.json"
REFERER = "https://nikkei225jp.com/data/saitei.php"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "saitei.csv"
JSON_PATH = ROOT / "data" / "saitei.json"
# turnover: プライム売買代金(億円), *_shares: 千株(日次), *_amount: 億円(週次)
FIELDS = ["date", "nikkei", "turnover", "buy_shares", "sell_shares", "buy_amount", "sell_amount"]
NUMERIC = FIELDS[1:]


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
        return v if isinstance(v, (int, float)) else None

    def oku(v):  # 百万円 → 億円
        return round(v / 100, 2) if isinstance(v, (int, float)) else None

    out = {}
    for row in rows:
        # 列: 0=日時(ms) 1=日経225終値 2=売買代金(百万円) 3=売残(千株) 4=買残(千株) 7=売残(百万円) 8=買残(百万円)
        if num(row[1]) is None:
            continue
        date = datetime.fromtimestamp(row[0] / 1000, JST).date().isoformat()
        out[date] = {
            "date": date,
            "nikkei": num(row[1]),
            "turnover": oku(row[2]),
            "buy_shares": num(row[4]),
            "sell_shares": num(row[3]),
            "buy_amount": oku(row[8]),
            "sell_amount": oku(row[7]),
        }
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
    # 元データは古い日の株数などを空欄で返すことがあるので、空欄で既存値を消さない
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
    amt = next(r for r in reversed(records) if r["buy_amount"] is not None)
    shr = next(r for r in reversed(records) if r["buy_shares"] is not None)
    print(f"{len(records)} 日分 (+{len(records) - before})  金額 {amt['date']} 買残={amt['buy_amount']}億円 売残={amt['sell_amount']}億円"
          f"  株数 {shr['date']} 買残={shr['buy_shares']}千株 売残={shr['sell_shares']}千株")


if __name__ == "__main__":
    sys.exit(main())
