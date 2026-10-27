// PER・PBR・国債金利ページ共通の描画処理。各ページは renderValuationPage(config) を呼ぶ。
//
// config:
//   basisToggle: true なら「加重平均 / 指数ベース」の切り替えを出す
//   charts: [{ id, title, height, digits, lines: [{ label, color, value(r, basis), width }], refs: [{ v, color }], hist }]
//   tiles(last, prev, basis): タイルの HTML
//   columns: [{ label, value(r, basis), digits, cls(v) }]
//   state(r, basis): 読み出し欄に出す目安（例: ['hot', '割高']）。不要なら省略
const BASIS = { w: '加重平均', i: '指数ベース' };

function renderValuationPage(config) {
  let rows = [], basis = 'w', months = 36, byTime = new Map(), built = [], showAll = false;

  const tile = (label, value, sub, hero) => `<div class="tile${hero ? ' hero' : ''}"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${sub || ''}</div></div>`;

  async function main() {
    const res = await fetch('data/valuation.json', { cache: 'no-cache' });
    const json = await res.json();
    rows = json.rows.map(r => Object.fromEntries(json.fields.map((k, i) => [k, r[i]])));
    rows.forEach(r => byTime.set(r.date, r));
    document.getElementById('updated').textContent = json.updated.replace('T', ' ');
    if (config.basisToggle) {
      document.getElementById('basis').hidden = false;
      document.querySelectorAll('#basis button').forEach(b => b.addEventListener('click', () => { basis = b.dataset.b; refresh(); }));
    }
    document.querySelectorAll('#range button').forEach(b => b.addEventListener('click', () => {
      document.querySelectorAll('#range button').forEach(x => x.setAttribute('aria-pressed', x === b));
      months = Number(b.dataset.m);
      setRange();
    }));
    document.getElementById('showAll').addEventListener('click', () => { showAll = true; renderTable(); });
    buildCharts();
    refresh();
    setRange();
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { applyTheme(); setData(); });
  }

  function refresh() {
    document.querySelectorAll('#basis button').forEach(x => x.setAttribute('aria-pressed', x.dataset.b === basis));
    document.querySelectorAll('.basis-name').forEach(el => el.textContent = config.basisToggle ? `（${BASIS[basis]}）` : '');
    const last = rows[rows.length - 1], prev = rows[rows.length - 2];
    document.getElementById('tiles').innerHTML = config.tiles(last, prev, basis, tile);
    renderTable();
    setData();
    showReadout(null);
  }

  function renderTable() {
    const LIMIT = 500;
    let h = '<thead><tr><th>日付</th>' + config.columns.map(c => `<th>${c.label}</th>`).join('') + '</tr></thead><tbody>';
    const from = showAll ? 0 : Math.max(0, rows.length - LIMIT);
    for (let i = rows.length - 1; i >= from; i--) {
      const r = rows[i];
      h += `<tr><td>${r.date}</td>` + config.columns.map(c => {
        const v = c.value(r, basis, rows[i - 1]);
        const cls = c.cls && v != null ? c.cls(v) : '';
        return `<td class="${cls || ''}">${fmt(v, c.digits)}</td>`;
      }).join('') + '</tr>';
    }
    document.getElementById('table').innerHTML = h + '</tbody>';
    document.getElementById('showAll').hidden = showAll || rows.length <= LIMIT;
  }

  function buildCharts() {
    const wrap = document.getElementById('charts');
    for (const c of config.charts) {
      wrap.insertAdjacentHTML('beforeend', `<div class="chart-title">${c.title}${c.note ? `<span class="note"> ${c.note}</span>` : ''}</div><div id="${c.id}" style="height:${c.height}px"></div>`);
      const chart = LightweightCharts.createChart(document.getElementById(c.id), chartOptions(c.digits));
      const series = c.lines.map(l => c.hist
        ? chart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false })
        : chart.addLineSeries({ lineWidth: l.width || 1.5, priceLineVisible: false, crosshairMarkerRadius: 4 }));
      if (c.refs) for (const ref of c.refs) {
        series[0].createPriceLine({ price: ref.v, color: css(ref.color), lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '' });
      }
      if (c.refs) {
        // 基準線が常に見えるよう縦軸の範囲を広げる
        const lo = Math.min(...c.refs.map(r => r.v)), hi = Math.max(...c.refs.map(r => r.v));
        series[0].applyOptions({ autoscaleInfoProvider: base => {
          const r = base(); if (!r) return r;
          const pad = (hi - lo || Math.abs(hi) || 1) * 0.1;
          return { priceRange: { minValue: Math.min(r.priceRange.minValue, lo - pad), maxValue: Math.max(r.priceRange.maxValue, hi + pad) } };
        } });
      }
      built.push({ conf: c, chart, series });
    }
    applyTheme();
    syncTimeScales(built.map(b => b.chart));
    for (const src of built) src.chart.subscribeCrosshairMove(p => {
      showReadout(p.time);
      for (const dst of built) {
        if (dst === src) continue;
        const r = p.time && byTime.get(p.time);
        const v = r ? dst.conf.lines[0].value(r, basis) : null;
        if (v != null && isFinite(v)) dst.chart.setCrosshairPosition(v, p.time, dst.series[0]); else dst.chart.clearCrosshairPosition();
      }
    });
  }

  // 値がない日も時刻だけの点として入れ、全チャートの横位置をそろえる
  function setData() {
    for (const b of built) b.conf.lines.forEach((l, i) => {
      b.series[i].setData(rows.map((r, j) => {
        const v = l.value(r, basis, rows[j - 1]);
        if (v == null || !isFinite(v)) return { time: r.date };
        return b.conf.hist ? { time: r.date, value: v, color: css(v >= 0 ? l.color : (l.negColor || l.color)) } : { time: r.date, value: v };
      }));
    });
  }

  function applyTheme() {
    for (const b of built) {
      b.chart.applyOptions(chartOptions(b.conf.digits));
      b.conf.lines.forEach((l, i) => { if (!b.conf.hist) b.series[i].applyOptions({ color: css(l.color) }); });
    }
  }

  function showReadout(t) {
    const r = byTime.get(t) || rows[rows.length - 1];
    const parts = [`<span><b>${r.date}</b></span>`];
    for (const b of built) for (const l of b.conf.lines) {
      parts.push(`<span>${l.label} <b>${fmt(l.value(r, basis), b.conf.digits)}</b>${l.unit || ''}</span>`);
    }
    const st = config.state && config.state(r, basis);
    if (st) parts.push(`<span class="badge ${st[0]}">${st[1]}</span>`);
    document.getElementById('readout').innerHTML = parts.join('');
  }

  function setRange() {
    const ts = built[0].chart.timeScale();
    if (!months) { ts.fitContent(); return; }
    const last = rows[rows.length - 1].date;
    const d = new Date(last); d.setMonth(d.getMonth() - months);
    ts.setVisibleRange({ from: d.toISOString().slice(0, 10), to: last });
  }

  main().catch(e => { document.getElementById('error').textContent = 'データの読み込みに失敗しました: ' + e.message; });
}
