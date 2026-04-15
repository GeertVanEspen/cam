<?php
// website/api.php - Schone en consistente dashboard API
header('Content-Type: application/json');

date_default_timezone_set('Europe/Brussels');

$db_path = "/home/wwwdata/mpa_stats.db";
$media_dir = "./media";
$log_file = "/home/wwwdata/mpa_upload.log";
$melding_file = "/home/wwwdata/melding.uit";

$response = [
    'status' => 'success',
    'server_time' => date('H:i:s'),
    'detector_online' => false,
    'detector_status_text' => 'Offline',
    'last_db_entry_minutes_ago' => null,
    'meldingen_aan' => !file_exists($melding_file),
    'stats' => ['car_count' => 0, 'mpa_count' => 0, 'fps' => 0.0],
    'latest_photo' => null,
    'latest_video' => null,
    'recent_photos' => [],
    'log_lines' => []
];

// ====================== DETECTOR ONLINE STATUS ======================
try {
    if (file_exists($db_path)) {
        $pdo = new PDO("sqlite:" . $db_path);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $stmt = $pdo->query("
            SELECT ROUND((strftime('%s', 'now', 'localtime') - strftime('%s', timestamp)) / 60.0, 1) AS minutes_ago
            FROM mpa_stats 
            ORDER BY timestamp DESC 
            LIMIT 1
        ");

        if ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $minutes_ago = (float)$row['minutes_ago'];
            $response['last_db_entry_minutes_ago'] = $minutes_ago;

            if ($minutes_ago <= 7) {
                $response['detector_online'] = true;
                $response['detector_status_text'] = 'Online';
            } else {
                $hours = floor($minutes_ago / 60);
                $mins = floor($minutes_ago % 60);
                if ($hours >= 1) {
                    $response['detector_status_text'] = "Offline ({$hours}u {$mins}m geleden)";
                } else {
                    $response['detector_status_text'] = "Offline ({$mins}m geleden)";
                }
            }
        }
    }
} catch (Exception $e) {
    $response['detector_status_text'] = 'Offline (DB-fout)';
}

// ====================== STATISTIEKEN ======================
try {
    if (file_exists($db_path)) {
        $pdo = new PDO("sqlite:" . $db_path);
        $stmt = $pdo->query("SELECT * FROM mpa_stats ORDER BY timestamp DESC LIMIT 1");
        if ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $response['stats'] = [
                'car_count' => (int)$row['daily_car_count'],
                'mpa_count' => (int)$row['daily_mpa_count'],
                'fps' => round((float)$row['current_fps'], 1)
            ];
        }
    }
} catch (Exception $e) {}

// ====================== LAATSTE FOTO + VIDEO ======================
$jpg_files = glob($media_dir . "/*.jpg");
if (!empty($jpg_files)) {
    usort($jpg_files, fn($a, $b) => filemtime($b) - filemtime($a));
    $latest_jpg = $jpg_files[0];
    $base_name = pathinfo($latest_jpg, PATHINFO_FILENAME);

    $response['latest_photo'] = [
        'url' => basename($latest_jpg),
        'filename' => basename($latest_jpg)
    ];

    $possible_video = $media_dir . "/" . $base_name . ".mp4";
    if (file_exists($possible_video)) {
        $response['latest_video'] = [
            'url' => basename($possible_video),
            'filename' => basename($possible_video)
        ];
    }
}

// ====================== RECENTE FOTO'S (max 3, zonder duplicaat) ======================
if (!empty($jpg_files)) {
    usort($jpg_files, fn($a, $b) => filemtime($b) - filemtime($a));
    $response['recent_photos'] = array_map('basename', array_slice($jpg_files, 1, 3)); // skip eerste (laatste detectie)
}

// ====================== LOG ======================
if (file_exists($log_file)) {
    $lines = array_slice(file($log_file), -15);
    $response['log_lines'] = array_map('trim', $lines);
}

echo json_encode($response);
?>
