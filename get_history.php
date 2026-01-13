<?php
header('Content-Type: application/json');
include 'conn.php';

// Mengambil 20 data terbaru, created_at diubah aliasnya jadi timestamp untuk Flutter
$sql = "SELECT 
            moisture_level, 
            water_level, 
            pump_status, 
            created_at as timestamp 
        FROM sensor_data 
        ORDER BY id DESC LIMIT 20";

$result = $conn->query($sql);
$data = [];

if ($result) {
    while($r = $result->fetch_assoc()) {
        $r['moisture_level'] = (int)$r['moisture_level'];
        $r['water_level'] = (int)$r['water_level'];
        $data[] = $r;
    }
}

echo json_encode($data);
?>