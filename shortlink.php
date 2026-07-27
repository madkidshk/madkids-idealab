<?php
// generated-by: scripts/core/nlm-bridge/mk_shortlink.py + lab_ui_shell.py
header('Content-Type: text/html; charset=utf-8');
$MAP = __DIR__ . '/../l/links.json';
$STATS = __DIR__ . '/../l/stats.json';
$PUBLIC = 'https://madkids.hk/l';
function load_map($p){ $m = json_decode(@file_get_contents($p), true); return is_array($m) ? $m : array(); }
function hk_time($utc){ if(!$utc) return '—'; $t = strtotime($utc); return $t ? gmdate('m-d H:i', $t + 8*3600) : '—'; }
function save_map($p, $m){
  $dir = dirname($p);
  if (!is_dir($dir)) { @mkdir($dir, 0755, true); }
  file_put_contents($p, json_encode($m, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT), LOCK_EX);
}
function slugify($url){ return 'd' . substr(sha1($url), 0, 6); }
$msg = ''; $msg_ok = false; $new_short = '';
$map = load_map($MAP);
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $act = isset($_POST['act']) ? $_POST['act'] : '';
  if ($act === 'add') {
    $url = trim($_POST['url'] ?? '');
    $slug = trim($_POST['slug'] ?? '');
    $slug = preg_replace('/[^A-Za-z0-9_-]/', '', $slug);
    if (!preg_match('#^https?://#i', $url)) {
      $msg = '❌ 個 URL 要係 http:// 或 https:// 開頭';
    } else {
      if ($slug === '') { $slug = slugify($url); }
      $map[$slug] = $url;
      save_map($MAP, $map);
      $new_short = "$PUBLIC/$slug";
      $msg = "✅ 短鏈整好"; $msg_ok = true;
    }
  } elseif ($act === 'del') {
    $slug = preg_replace('/[^A-Za-z0-9_-]/', '', trim($_POST['slug'] ?? ''));
    if ($slug !== '' && isset($map[$slug])) { unset($map[$slug]); save_map($MAP, $map); $msg = "🗑️ 已刪 $slug"; $msg_ok = true; }
  }
  $map = load_map($MAP);
}
$stats = load_map($STATS);
$total_clicks = 0; $peak = 0;
foreach ($stats as $sv) { $c = intval($sv['c'] ?? 0); $total_clicks += $c; if ($c > $peak) $peak = $c; }
$ABUSE = 200;
krsort($map);
?><!DOCTYPE html><html lang="zh-HK"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔗 短鏈工具</title>
<style>:root{--bg:#f4f5f7;--card:#fff;--ink:#1b1f27;--mut:#717784;--line:#e7e9ee;--accent:#4f46e5;--grn:#15a34a;--red:#dc2626;--sh:0 1px 2px rgba(20,24,40,.04),0 4px 14px rgba(20,24,40,.05)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang HK","Microsoft JhengHei",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:22px 15px 80px}
h1{font-size:25px;font-weight:800;margin:.1em 0;letter-spacing:-.01em} .sub{color:var(--mut);font-size:13px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:560px){.grid{grid-template-columns:1fr 1fr}}
.card{display:block;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:16px;padding:17px 18px;box-shadow:var(--sh)}
.card:active{border-color:#cfd3dc}
.dept{font-size:21px;font-weight:800} .topic{color:var(--mut);font-size:14px;margin:3px 0 11px;min-height:20px}
.due-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.due{display:inline-block;font-size:12px;font-weight:800;border-radius:999px;padding:3px 10px}
.due.ok{background:#e7f7ee;color:var(--grn)} .due.over{background:#fdeaea;color:var(--red)} .due.none{background:#eef0f3;color:var(--mut)}
.dday{color:var(--mut);font-size:12.5px;font-weight:600}
.go{margin-top:12px;color:var(--accent);font-size:13px;font-weight:700}
.empty{color:var(--mut)}
.sect{font-size:16px;font-weight:800;margin:24px 0 10px;border-left:4px solid var(--sect);padding-left:9px}
.sect.tight{margin-top:6px}
details.soft{background:#fff;border:1px solid var(--line);border-radius:14px;padding:4px 16px;margin:18px 0;box-shadow:var(--sh)}
details.soft>summary{cursor:pointer;font-weight:700;font-size:14px;padding:12px 0;list-style:none;color:var(--mut)}
details.soft>summary::-webkit-details-marker{display:none} details.soft>summary::before{content:"▸ ";} details.soft[open]>summary::before{content:"▾ ";}
details.soft .grid{margin:6px 0 12px}
footer{color:var(--mut);font-size:12px;border-top:1px solid var(--line);margin-top:30px;padding-top:14px}.titlerow{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:nowrap}
.titlerow h1{margin:0;min-width:0}
.hdrbtns{flex:none;display:flex;gap:7px;align-items:center}
.homebtn,.refbtn{flex:none;white-space:nowrap;font-size:16px;line-height:1;text-decoration:none;background:#eef0fe;border:1px solid #dcdffb;border-radius:8px;padding:5px 9px;color:#222}
.refbtn{cursor:pointer}
.labbtn{flex:none;white-space:nowrap;font-size:13px;line-height:1;text-decoration:none;border-radius:9px;padding:7px 10px;font-weight:800;border:1px solid transparent}
.labbtn.mk{background:#fff5f5;color:#EE382F;border-color:#f3b4ae}
.labbtn.mm{background:#fff7ed;color:#d97706;border-color:#fdba74}
@media(max-width:480px){.homebtn,.refbtn{font-size:14px;padding:5px 8px}}.rolesub{max-width:1100px;margin:0 auto 12px;font-size:12.5px;color:#475569;font-weight:700;background:#f1f5f9;border-left:3px solid #94a3b8;border-radius:7px;padding:7px 12px}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;max-width:1100px;margin:0 auto 14px}
.card{background:#fff;border:1px solid #e7e9ee;border-radius:14px;padding:18px;box-shadow:0 1px 2px rgba(20,24,40,.04),0 4px 14px rgba(20,24,40,.05);margin:0 auto 14px;max-width:1100px}
label{display:block;font-size:13px;font-weight:700;color:#717784;margin:10px 0 5px}
input[type=text],input[type=url]{width:100%;padding:11px 13px;border:1px solid #e7e9ee;border-radius:11px;font-size:15px;font-family:inherit}
input:focus{outline:none;border-color:#4f46e5}
.hint{color:#717784;font-size:12px;margin-top:4px}
button{margin-top:14px;background:#4f46e5;color:#fff;border:0;border-radius:9px;padding:10px 16px;font-size:14px;font-weight:800;cursor:pointer}
button.del{background:transparent;color:#dc2626;padding:6px 10px;font-size:12px;font-weight:700;margin:0}
.flash{border-radius:12px;padding:12px 14px;margin:0 auto 14px;max-width:1100px;font-weight:700}
.flash.ok{background:#e7f7ee;color:#15a34a}.flash.err{background:#fdeaea;color:#dc2626}
.result{background:#f0f2ff;border:1px solid #d9dcff;border-radius:12px;padding:14px;margin-top:12px}
.result .u{font-size:18px;font-weight:800;color:#4f46e5;word-break:break-all}
.row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 0;border-top:1px solid #e7e9ee}
.row:first-child{border-top:0}
.row .s{font-weight:800;color:#4f46e5;word-break:break-all}
.row .t{color:#717784;font-size:12.5px;word-break:break-all;margin-top:2px}
.copy{background:#eef0f3;border:0;border-radius:9px;padding:6px 11px;font-size:12px;font-weight:700;cursor:pointer;color:#1b1f27}
.grow{flex:1;min-width:0}
.stat{flex:1;background:#fff;border:1px solid #e7e9ee;border-radius:14px;padding:12px 14px;box-shadow:0 1px 2px rgba(20,24,40,.04),0 4px 14px rgba(20,24,40,.05);text-align:center}
.stat .n{font-size:24px;font-weight:800;line-height:1.1}.stat .k{font-size:11.5px;color:#717784;font-weight:700;margin-top:2px}
.stat.warn .n{color:#dc2626}
.hits{display:inline-block;font-size:12px;font-weight:800;background:#eef0f3;color:#717784;border-radius:999px;padding:2px 9px;white-space:nowrap}
.hits.hot{background:#fdeaea;color:#dc2626}
.last{color:#717784;font-size:11.5px;margin-top:2px}
@media(max-width:780px){.stats{grid-template-columns:1fr}.row{flex-wrap:wrap}.copy,button.del{margin-top:0}}
</style></head><body><div class="wrap">
<!-- generated-by: scripts/core/nlm-bridge/lab_ui_shell.py -->
<div class='titlerow'><h1>🔗 短鏈工具</h1><span class='hdrbtns'><a class='homebtn' href='.' title='總目錄'>🏠</a><button class='refbtn' onclick="location.href=location.pathname+'?t='+Date.now()+location.hash" title='重新載入'>🔄</button></span></div>
<div class="sub">貼長 URL → 出 <b>madkids.hk/l/…</b> 真 302 短鏈（自家 domain，冇廣告頁）</div>
<!-- generated-by: scripts/core/nlm-bridge/mk_shortlink.py + lab_ui_shell.py -->
<?php if ($msg): ?><div class="flash <?= $msg_ok ? 'ok' : 'err' ?>"><?= htmlspecialchars($msg) ?></div><?php endif; ?>
<div class="rolesub">🧰 <b>工具</b> · 用自家 domain 做真 302 短鏈；上面先整 link，下面再睇現有清單同異常點擊</div>
<div class="stats">
  <div class="stat"><div class="n"><?= count($map) ?></div><div class="k">條短鏈</div></div>
  <div class="stat"><div class="n"><?= number_format($total_clicks) ?></div><div class="k">總點擊</div></div>
  <div class="stat <?= $peak >= $ABUSE ? 'warn' : '' ?>"><div class="n"><?= number_format($peak) ?></div><div class="k">單條最高<?= $peak >= $ABUSE ? ' ⚠️' : '' ?></div></div>
</div>
<?php if ($peak >= $ABUSE): ?><div class="flash err">⚠️ 有短鏈點擊異常高（≥<?= $ABUSE ?>），下面紅色嗰條留意有冇被濫用。</div><?php endif; ?>
<div class="card">
  <form method="post">
    <input type="hidden" name="act" value="add">
    <label>長 URL</label>
    <input type="url" name="url" placeholder="https://docs.google.com/…" required>
    <label>自訂 slug（可留空，自動生）</label>
    <input type="text" name="slug" placeholder="例:boc-brief（→ madkids.hk/l/boc-brief）">
    <div class="hint">只准英文字母/數字/連字號。留空 = 自動 hash slug。</div>
    <button type="submit">整短鏈</button>
  </form>
  <?php if ($new_short): ?>
  <div class="result">
    <div class="u" id="ns"><?= htmlspecialchars($new_short) ?></div>
    <button class="copy" onclick="cp('<?= htmlspecialchars($new_short) ?>',this)">複製</button>
  </div>
  <?php endif; ?>
</div>
<div class="card">
  <div style="font-weight:800;margin-bottom:6px">現有短鏈（<?= count($map) ?>）</div>
  <?php if (!$map): ?><div class="hint">未有短鏈。</div><?php endif; ?>
  <?php foreach ($map as $slug => $url): $c = intval($stats[$slug]['c'] ?? 0); $lt = $stats[$slug]['l'] ?? ''; ?>
    <div class="row">
      <div class="grow">
        <div class="s"><?= htmlspecialchars($PUBLIC.'/'.$slug) ?></div>
        <div class="t">→ <?= htmlspecialchars($url) ?></div>
        <div class="last">最後點擊 <?= htmlspecialchars(hk_time($lt)) ?></div>
      </div>
      <span class="hits <?= $c >= $ABUSE ? 'hot' : '' ?>"><?= number_format($c) ?> 點</span>
      <button class="copy" onclick="cp('<?= htmlspecialchars($PUBLIC.'/'.$slug) ?>',this)">複製</button>
      <form method="post" onsubmit="return confirm('刪 <?= htmlspecialchars($slug) ?>?')" style="margin:0">
        <input type="hidden" name="act" value="del"><input type="hidden" name="slug" value="<?= htmlspecialchars($slug) ?>">
        <button class="del" type="submit">刪</button>
      </form>
    </div>
  <?php endforeach; ?>
</div>

<footer>短鏈存 <code>/l/links.json</code> · router <code>/l/</code> 做 302 · 同 <code>mk_shortlink.py</code> 共用</footer>
</div><script>
function cp(t,b){navigator.clipboard.writeText(t).then(function(){var o=b.textContent;b.textContent='✓ 複製咗';setTimeout(function(){b.textContent=o;},1200);});}
</script></body></html>