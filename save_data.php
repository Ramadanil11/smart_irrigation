<?php
header('Content-Type: application/json');
include 'conn.php';
date_default_timezone_set('Asia/Jakarta');

$moisture = $_POST['moisture'] ?? 0;
$water    = $_POST['water'] ?? 0;
$nowTime  = date("H:i:s");
$nowFull  = date("Y-m-d H:i:s");

// 1. Ambil data kontrol
$ctrl_query = $conn->query("SELECT * FROM pump_control WHERE id=1");
$ctrl = $ctrl_query->fetch_assoc();

if (!$ctrl) {
    $targetStatus = 'OFF';
} else {
    // --- PERBAIKAN LOGIKA JEDA ---
    // Cek apakah kolom pause_until ada isinya
    if (!empty($ctrl['pause_until'])) {
        if ($nowFull >= $ctrl['pause_until']) {
            // JIKA WAKTU SUDAH LEWAT: Langsung hapus di DB
            $conn->query("UPDATE pump_control SET pause_until = NULL WHERE id=1");
            $ctrl['pause_until'] = null; // Update variabel lokal agar tidak masuk ke blok OFF
        }
    }

    // 2. Tentukan status dasar (Manual Target)
    $targetStatus = $ctrl['manual_target'];

    // 3. Cek Jadwal Otomatis (Prioritas Tinggi)
    $sch_query = $conn->query("SELECT * FROM pump_schedules WHERE is_active=1 AND '$nowTime' BETWEEN on_time AND off_time LIMIT 1");
    if ($sch_query->num_rows > 0) {
        $targetStatus = 'ON';
    }

    // 4. Cek Jeda (Prioritas Tertinggi / Final Check)
    // Jika pause_until masih ada isinya (berarti belum lewat waktunya)
    if (!empty($ctrl['pause_until'])) {
        $targetStatus = 'OFF';
    }
}

// 5. Simpan ke history
$sql = "INSERT INTO sensor_data (moisture_level, water_level, pump_status) VALUES ($moisture, $water, '$targetStatus')";

if ($conn->query($sql) === TRUE) {
    echo json_encode([
        "status" => "success", 
        "command" => $targetStatus
    ]);
} else {
    echo json_encode(["status" => "error", "message" => $conn->error]);
}
?>