# 騰落レシオ記録

[nikkei225jp.com の騰落レシオ](https://nikkei225jp.com/data/touraku.php) の元データ（東証プライムの値上がり・値下がり銘柄数）を毎営業日 GitHub Actions で取得し、`data/` に蓄積します。

- チャート: GitHub Pages の `index.html`（25 / 15 / 10 / 6 日騰落レシオ + 日経225）
- データ: [`data/touraku.csv`](data/touraku.csv)（画面用は `data/touraku.json`）
- 取得: `.github/workflows/update.yml` が平日 18:40 / 21:10 JST に実行。Actions タブから手動実行も可

元サイトは直近約2年分のみ配信しているため、2024年10月以降が初期データです。以降は毎日追記されるので2年を超えて履歴が残ります。

騰落レシオ(N日) = N日間の値上がり銘柄数合計 ÷ 値下がり銘柄数合計 × 100

```
python3 scripts/fetch.py   # 手動更新
```
