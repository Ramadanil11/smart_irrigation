<?php
header('Content-Type: application/json');
include 'conn.php';
date_default_timezone_set('Asia/Jakarta');

$type = $_POST['type'] ?? '';

if ($type == 'manual') {
    $val = $_POST['target'] ?? 'OFF';
    // Jika user menekan tombol ON/OFF secara manual, hapus jeda dan update target
    $conn->query("UPDATE pump_control SET manual_target = '$val', pause_until = NULL WHERE id=1");
} 
else if ($type == 'pause') {
    $min = intval($_POST['minutes'] ?? 0);
    $until = date("Y-m-d H:i:s", strtotime("+$min minutes"));
    // PERBAIKAN: Hanya set pause_until saja, manual_target biarkan tetap ON
    $conn->query("UPDATE pump_control SET pause_until = '$until' WHERE id=1");
}

echo json_encode(["status" => "success"]);
?>