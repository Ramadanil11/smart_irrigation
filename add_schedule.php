<?php
// add_schedule.php
header('Content-Type: application/json');
include 'conn.php';

$on = $_POST['on_time'] ?? '';
$off = $_POST['off_time'] ?? '';

if($on && $off) {
    // Nonaktifkan jadwal lama, aktifkan yang baru
    $conn->query("UPDATE pump_schedules SET is_active = 0");
    $sql = "INSERT INTO pump_schedules (on_time, off_time, is_active) VALUES ('$on', '$off', 1)";
    if($conn->query($sql)) {
        echo json_encode(["status" => "success"]);
    } else {
        echo json_encode(["status" => "error"]);
    }
}
?>