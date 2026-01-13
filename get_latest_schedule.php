<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
include 'conn.php';

$sql = "SELECT on_time, off_time FROM pump_schedules WHERE is_active = 1 ORDER BY id DESC LIMIT 1";
$result = $conn->query($sql);

if ($result && $result->num_rows > 0) {
    $row = $result->fetch_assoc();
    echo json_encode([
        "status" => "success",
        "data" => [
            "on_time" => substr($row['on_time'], 0, 5),
            "off_time" => substr($row['off_time'], 0, 5)
        ]
    ]);
} else {
    echo json_encode([
        "status" => "empty",
        "message" => "Tidak ada jadwal aktif"
    ]);
}
?>