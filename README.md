# 市場データの記録（騰落レシオ・信用残・裁定残・PER・PBR・国債金利）

[nikkei225jp.com の騰落レシオ](https://nikkei225jp.com/data/touraku.php) の元データ（東証プライムの値上がり・値下がり銘柄数）を毎営業日 GitHub Actions で取得し、`data/` に蓄積します。

- チャート: GitHub Pages でタブ切り替え
  - `index.html` 騰落レシオ（25 / 15 / 10 / 6 日 + 日経225）
  - `sinyou.html` 信用残・信用倍率・信用評価損益率（週次、[元ページ](https://nikkei225jp.com/data/sinyou.php)）
  - `saitei.html` 裁定買い残・売り残（金額は週次・株数は日次、[元ページ](https://nikkei225jp.com/data/saitei.php)）
  - `per.html` / `pbr.html` / `kokusai.html` 日経225 PER・PBR（加重平均/指数ベース）、10年国債利回り・イールドスプレッド（日次、[元ページ](https://nikkei225jp.com/data/per.php)）
- データ: [`data/touraku.csv`](data/touraku.csv)、[`data/sinyou.csv`](data/sinyou.csv)、[`data/saitei.csv`](data/saitei.csv)、[`data/valuation.csv`](data/valuation.csv)（画面用は同名の `.json`）
  - 信用残の金額は億円、株数は千株。2009年6月以降の週次データ
  - 裁定残の金額は億円（2024年10月〜）、株数は千株（2025年11月〜）
  - valuation: PER/PBR/配当利回り（_w=加重平均, _i=指数ベース）と10年国債利回り(%)。2009年6月〜
- 取得: `.github/workflows/update.yml` が平日 18:40 / 21:10 JST に実行。Actions タブから手動実行も可

元サイトは直近約2年分のみ配信しているため、2024年10月以降が初期データです。以降は毎日追記されるので2年を超えて履歴が残ります。

騰落レシオ(N日) = N日間の値上がり銘柄数合計 ÷ 値下がり銘柄数合計 × 100

```
python3 scripts/fetch.py          # 騰落レシオを手動更新
python3 scripts/fetch_sinyou.py   # 信用残を手動更新
python3 scripts/fetch_saitei.py   # 裁定残を手動更新
python3 scripts/fetch_valuation.py   # PER・PBR・国債利回りを手動更新
```
