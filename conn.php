<?php
$host = "localhost";
$user = "root";
$pass = ""; 
$db   = "db_irigasi";

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    header('Content-Type: application/json');
    die(json_encode(["status" => "error", "message" => "Koneksi database gagal"]));
}
?>