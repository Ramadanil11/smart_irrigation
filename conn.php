<?php
// Mengambil data dari environment variables Railway
$host = getenv('mysql.railway.internal');
$user = getenv('root');
$pass = getenv('iSEQEeYOZUjEzUkBiShOSKACGOqguOuK');
$db   = getenv('railway');
$port = getenv('3306');

$conn = new mysqli($host, $user, $pass, $db, $port);

if ($conn->connect_error) {
    header('Content-Type: application/json');
    die(json_encode(["status" => "error", "message" => "Koneksi gagal"]));
}
?>
