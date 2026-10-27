// 各ページ共通のヘルパー（色トークンの読み出し、数値整形、チャートの基本設定）
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = (v, d = 2) => v == null ? '-' : Number(v).toLocaleString('ja-JP', { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v, d = 2) => v == null || !isFinite(v) ? '-' : (v >= 0 ? '+' : '') + fmt(v, d) + '%';

// digits: 縦軸の小数点以下の桁数（桁区切り付きで表示）
function chartOptions(digits = 2) {
  return {
    autoSize: true,
    layout: { background: { color: css('--surface-1') }, textColor: css('--text-secondary'), fontSize: 11 },
    grid: { vertLines: { visible: false }, horzLines: { color: css('--grid') } },
    rightPriceScale: { borderVisible: false, minimumWidth: 70 },
    timeScale: { borderVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Magnet },
    localization: { locale: 'ja-JP', dateFormat: 'yyyy/MM/dd', priceFormatter: v => fmt(v, digits) },
    handleScale: { axisPressedMouseMove: { price: false } },
  };
}

// 複数チャートの表示範囲を同期する
function syncTimeScales(charts) {
  let syncing = false;
  for (const a of charts) a.timeScale().subscribeVisibleLogicalRangeChange(r => {
    if (syncing || !r) return;
    syncing = true;
    for (const b of charts) if (b !== a) b.timeScale().setVisibleLogicalRange(r);
    syncing = false;
  });
}
