<?php
include 'conn.php';

$sql = "SELECT moisture_level, pump_status, created_at 
        FROM sensor_data 
        ORDER BY id DESC LIMIT 1";

$result = $conn->query($sql);

if ($result && $row = $result->fetch_assoc()) {
    echo json_encode([
        "success" => true,
        "data" => [
            "moisture" => (int) ($row['moisture_level'] ?? 0),
            "pump" => $row['pump_status'] ?? "OFF",
            "mode" => "AUTO",
            "time" => $row['created_at'] ?? ""
        ]
    ]);
} else {
    echo json_encode([
        "success" => true,
        "data" => [
            "moisture" => 0,
            "pump" => "OFF",
            "mode" => "AUTO",
            "time" => ""
        ]
    ]);
}

$conn->close();
