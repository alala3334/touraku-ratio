#!/usr/bin/env python3
"""nikkei225jp.com の信用残・信用倍率・信用評価損益率（週次）を取得し、data/ に蓄積する。

元データ: https://nikkei225jp.com/data/sinyou.php が読み込む dailyweek2.json。
日付は各週の最終営業日（多くは金曜）。取得した行は既存の履歴に日付単位で
上書き・追加する。
"""
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = "https://nikkei225jp.com/_data/_nfsDATA/data_DAY/dailyweek2.json"
REFERER = "https://nikkei225jp.com/data/sinyou.php"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "sinyou.csv"
JSON_PATH = ROOT / "data" / "sinyou.json"
# sell/buy_shares: 千株, sell/buy_amount: 億円, ratio: 信用倍率, pnl: 信用評価損益率(%)
FIELDS = ["date", "nikkei", "sell_shares", "sell_amount", "buy_shares", "buy_amount", "ratio", "pnl"]
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

    out = {}
    for row in rows:
        # 列: 0=日時(ms) 1=日経225終値 3=売残(千株) 4=売残(百万円) 5=買残(千株) 6=買残(百万円) 7=評価損益率 8=信用倍率
        sell_amt, buy_amt = num(row[4]), num(row[6])
        rec = {
            "nikkei": num(row[1]),
            "sell_shares": num(row[3]),
            "sell_amount": round(sell_amt / 100, 2) if sell_amt else None,
            "buy_shares": num(row[5]),
            "buy_amount": round(buy_amt / 100, 2) if buy_amt else None,
            "ratio": num(row[8]),
            "pnl": num(row[7]),
        }
        # 信用残の行がない日（週の途中の営業日）は飛ばす
        if rec["buy_amount"] is None and rec["pnl"] is None:
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
    save(records)
    last = records[-1]
    print(f"{len(records)} 週分 (+{len(records) - before})  最新 {last['date']}  評価損益率={last['pnl']} 信用倍率={last['ratio']} 買残={last['buy_amount']}億円")


if __name__ == "__main__":
    sys.exit(main())
