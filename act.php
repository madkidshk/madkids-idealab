<?php
// act.php — 單一通用雲端 queue / command bus（任何裝置觸發 dashboard 掣／貼 link）。
// push 一個 {route,params} 入 queue → 主機 listener n0c_queue_loop poll dispatch。
// 有結果嘅 route（photoid）由 listener FTP 寫 act_data/<route>_{state,results}.json，dashboard 用 ?action=status&topic= 讀。
// ⛔ params 只收英數_-（WAF/注入安全）。⛔ 唔好改檔名做 cmd.php/shell.php（n0c WAF 封）。
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
$dir = __DIR__ . '/act_data';
if (!is_dir($dir)) @mkdir($dir, 0755, true);
$qf = "$dir/queue.json";
@file_put_contents("$dir/hits.log", date("H:i:s")." ".($_SERVER["REQUEST_URI"]??"")." ua=".substr($_SERVER["HTTP_USER_AGENT"]??"",0,30)."\n", FILE_APPEND);
function rd($f){ $d=@file_get_contents($f); return $d?json_decode($d,true):null; }
$a = isset($_GET['action']) ? $_GET['action'] : '';
if (isset($_GET['push'])) {
  $allow = array('route','client','stage','po','engine','by','kind','target','cid','folder');
  $item = array('ts'=>time());
  foreach ($allow as $k) { if (isset($_GET[$k])) $item[$k] = preg_replace('/[^A-Za-z0-9_\-]/','',$_GET[$k]); }
  if (empty($item['route'])) { echo json_encode(array('err'=>'no route')); exit; }
  $q = rd($qf) ?: array(); $q[] = $item; file_put_contents($qf, json_encode($q));
  echo json_encode(array('ok'=>true)); exit;
}
if ($a==='hits') { echo @file_get_contents("$dir/hits.log") ?: "(冇 hit)"; exit; }
if ($a==='pending') { $q = rd($qf) ?: array(); file_put_contents($qf, json_encode(array())); echo json_encode($q); exit; }
if ($a==='status') {
  $t = isset($_GET['topic']) ? preg_replace('/[^a-z0-9_]/','',$_GET['topic']) : '';
  echo json_encode(array('state'=>rd("$dir/{$t}_state.json"), 'rows'=>(rd("$dir/{$t}_results.json") ?: array()))); exit;
}
echo json_encode(array('err'=>'unknown action'));
