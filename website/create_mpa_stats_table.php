<?php
date_default_timezone_set('Europe/Brussels');
$db_path = "/home/wwwdata/mpa_stats.db";

try {
    $pdo = new PDO("sqlite:" . $db_path);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS mpa_stats (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp           DATETIME DEFAULT (datetime('now','localtime')),
            daily_car_count     INTEGER NOT NULL,
            daily_mpa_count     INTEGER NOT NULL,
            current_fps         REAL NOT NULL,
            imageCtr            INTEGER NOT NULL
        )
    ");

    echo "Tabel 'mpa_stats' succesvol aangemaakt of bestond al.<br>";
    echo "Database locatie: " . $db_path;

} catch (Exception $e) {
    echo "Fout bij aanmaken tabel: " . $e->getMessage();
}
?>
