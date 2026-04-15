<?php
// api.php - Schone versie met correcte timezone handling
header('Content-Type: application/json');

date_default_timezone_set('Europe/Brussels');

$db_path = "/home/wwwdata/mpa_stats.db";
$media_dir = "./media";
$log_file = "/home/wwwdata/mpa_upload.log";
$melding_file = "/home/wwwdata/melding.uit";


// ====================== STATISTIEKEN OVERZICHT ======================
if (isset($_GET['type']) && $_GET['type'] === 'stats_overview') {
    $result = [
        'today'      => ['cars' => 0, 'mpa' => 0],
        'yesterday'  => ['cars' => 0, 'mpa' => 0],
        'this_week'  => ['cars' => 0, 'mpa' => 0],
        'this_month' => ['cars' => 0, 'mpa' => 0]
    ];

    try {
        if (file_exists($db_path)) {
            $pdo = new PDO("sqlite:" . $db_path);

            $queries = [
                'today'     => "date(timestamp) = date('now', 'localtime')",
                'yesterday' => "date(timestamp) = date('now', '-1 day', 'localtime')",
                'this_week' => "strftime('%Y-%W', timestamp) = strftime('%Y-%W', 'now', 'localtime')",
                'this_month'=> "strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now', 'localtime')"
            ];

            foreach ($queries as $key => $where) {
                $stmt = $pdo->prepare("
                    SELECT MAX(daily_car_count) as cars, MAX(daily_mpa_count) as mpa
                    FROM mpa_stats
                    WHERE $where
                ");
                $stmt->execute();
                if ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                    $result[$key] = [
                        'cars' => (int)$row['cars'],
                        'mpa'  => (int)$row['mpa']
                    ];
                }
            }
        }
    } catch (Exception $e) {
        // Bij error blijven de waarden op 0
    }

    echo json_encode($result);
    exit;
}



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

try {
    if (file_exists($db_path)) {
        $pdo = new PDO("sqlite:" . $db_path);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        // Correcte lokale tijd berekening
        $stmt = $pdo->query("
            SELECT
                ROUND((strftime('%s', 'now', 'localtime') - strftime('%s', timestamp)) / 60.0, 1) AS minutes_ago,
                timestamp
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
                $mins  = floor($minutes_ago % 60);

                if ($hours >= 1) {
                    $response['detector_status_text'] = "Offline ({$hours}u {$mins}m geleden)";
                } elseif ($mins >= 5) {
                    $response['detector_status_text'] = "Offline ({$mins}m geleden)";
                } else {
                    $response['detector_status_text'] = "Offline (net geleden)";
                }
            }
        }
    }
} catch (Exception $e) {
    $response['detector_status_text'] = 'Offline (DB-fout)';
}

// Statistieken
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

// Foto + Video
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

// Recente foto's
if (!empty($jpg_files)) {
    usort($jpg_files, fn($a, $b) => filemtime($b) - filemtime($a));
    $response['recent_photos'] = array_map('basename', array_slice($jpg_files, 0, 3));
}

// Log
if (file_exists($log_file)) {
    $lines = array_slice(file($log_file), -15);
    $response['log_lines'] = array_map('trim', $lines);
}

echo json_encode($response);
?>
