<?php
// photoid.php — 客戶相→產品識別 雲端 queue（任何裝置觸發，主機 listener poll 嚟跑）。
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
$dir = __DIR__ . '/photoid_data';
if (!is_dir($dir)) @mkdir($dir, 0755, true);
$qf = "$dir/queue.json"; $rf = "$dir/results.json"; $sf = "$dir/state.json";
function rd($f){ $d=@file_get_contents($f); return $d?json_decode($d,true):null; }
$a = isset($_GET['action']) ? $_GET['action'] : '';

if (isset($_GET['submit'])) {                 // dashboard 送出 folder link
  $q = rd($qf) ?: [];
  $q[] = array('folder'=>$_GET['submit'], 'ts'=>time());
  file_put_contents($qf, json_encode($q));
  file_put_contents($sf, json_encode(array('running'=>true,'ts'=>date('Y-m-d H:i'))));
  echo json_encode(array('ok'=>true)); exit;
}
if ($a==='pending') {                          // listener 認領 pending（清空 queue）
  $q = rd($qf) ?: [];
  file_put_contents($qf, json_encode(array()));
  echo json_encode($q); exit;
}
if ($a==='putresults') {                       // listener 寫返結果
  $body = file_get_contents('php://input');
  if ($body) file_put_contents($rf, $body);
  file_put_contents($sf, json_encode(array('running'=>false,'ts'=>date('Y-m-d H:i'))));
  echo json_encode(array('ok'=>true)); exit;
}
if ($a==='status') {                           // dashboard poll 狀態+結果
  echo json_encode(array('state'=>rd($sf), 'rows'=>(rd($rf) ?: array()))); exit;
}
echo json_encode(array('err'=>'unknown action'));
