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
        'today'           => ['cars' => 0, 'mpa' => 0],
        'yesterday'       => ['cars' => 0, 'mpa' => 0],
        'this_week'       => ['cars' => 0, 'mpa' => 0],
        'previous_week'   => ['cars' => 0, 'mpa' => 0],
        'this_month'      => ['cars' => 0, 'mpa' => 0],
        'previous_month'  => ['cars' => 0, 'mpa' => 0],
        'this_year'       => ['cars' => 0, 'mpa' => 0],
        'previous_year'   => ['cars' => 0, 'mpa' => 0]
    ];

    try {
        if (file_exists($db_path)) {
            $pdo = new PDO("sqlite:" . $db_path);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            // Haal per dag de MAX cumulatieve waarde op (timestamp is al lokale tijd)
            $stmt = $pdo->query("
                SELECT
                    date(timestamp) as day,
                    MAX(daily_car_count) as max_cars,
                    MAX(daily_mpa_count) as max_mpa
                FROM mpa_stats
                GROUP BY day
                ORDER BY day
            ");

/*
2026-04-04|147|3
2026-04-05|191|1
2026-04-06|55|0
2026-04-09|133|5
2026-04-10|224|3
2026-04-11|258|4
2026-04-12|219|1
2026-04-13|283|1
2026-04-14|255|1
2026-04-15|325|1
2026-04-16|392|2
2026-04-17|92|0
*/

            $daily = [];
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                $daily[$row['day']] = [
                    'cars' => (int)$row['max_cars'],
                    'mpa'  => (int)$row['max_mpa']
                ];
            }

            // Helper om som van max-waarden over meerdere dagen te berekenen
            $sum_days = function($dates) use ($daily) {
                $cars = 0; $mpa = 0;
                foreach ($dates as $d) {
                    if (isset($daily[$d])) {
                        $cars += $daily[$d]['cars'];
                        $mpa  += $daily[$d]['mpa'];
                    }
                }
                return ['cars' => $cars, 'mpa' => $mpa];
            };

            // Vandaag en Gisteren
            $today_str = date('Y-m-d');
            $yest_str  = date('Y-m-d', strtotime('-1 day'));

            $result['today']     = $daily[$today_str] ?? ['cars' => 0, 'mpa' => 0];
            $result['yesterday'] = $daily[$yest_str]  ?? ['cars' => 0, 'mpa' => 0];

            /*
            // Deze week (laatste 7 dagen)
            $week_days = [];
            for ($i = 0; $i < 7; $i++) {
                $week_days[] = date('Y-m-d', strtotime("-$i days"));
            }
            $result['this_week'] = $sum_days($week_days); */

            // Deze week (vanaf afgelopen maandag t/m vandaag)
            $week_days = [];
            $monday = strtotime('monday this week');
            $today  = strtotime('today');
            // Loop vanaf maandag tot en met vandaag.
            for ($d = $monday; $d <= $today; $d = strtotime('+1 day', $d)) {
                $week_days[] = date('Y-m-d', $d);
            }
            $result['this_week'] = $sum_days($week_days);

            /*
            // Vorige week
            $pweek_days = [];
            for ($i = 7; $i < 14; $i++) {
                $pweek_days[] = date('Y-m-d', strtotime("-$i days"));
            }
            $result['previous_week'] = $sum_days($pweek_days); */

            // Vorige week (maandag t/m zondag)
            $pweek_days = [];
            $last_monday = strtotime('monday last week');
            for ($i = 0; $i < 7; $i++) {
                $pweek_days[] = date('Y-m-d', strtotime("+$i days", $last_monday));
            }
            $result['previous_week'] = $sum_days($pweek_days);

            /*
            // Deze maand (laatste 31 dagen)
            $month_days = [];
            for ($i = 0; $i < 31; $i++) {
                $month_days[] = date('Y-m-d', strtotime("-$i days"));
            }
            $result['this_month'] = $sum_days($month_days);

            // Vorige maand (vorige 31 dagen)
            $pmonth_days = [];
            for ($i = 31; $i < 62; $i++) {
                $pmonth_days[] = date('Y-m-d', strtotime("-$i days"));
            }
            $result['previous_month'] = $sum_days($pmonth_days); */

            // --- Deze maand (vanaf de 1e t/m vandaag) ---
            $month_days = [];
            $first_day_this_month = strtotime('first day of this month 00:00:00');
            $today = strtotime('today 00:00:00');
            for ($d = $first_day_this_month; $d <= $today; $d = strtotime('+1 day', $d)) {
                $month_days[] = date('Y-m-d', $d);
            }
            $result['this_month'] = $sum_days($month_days);


            // --- Vorige maand (volledige kalendermaand) ---
            $pmonth_days = [];
            $first_day_last_month = strtotime('first day of last month 00:00:00');
            $last_day_last_month  = strtotime('last day of last month 00:00:00');
            for ($d = $first_day_last_month; $d <= $last_day_last_month; $d = strtotime('+1 day', $d)) {
                $pmonth_days[] = date('Y-m-d', $d);
            }
            $result['previous_month'] = $sum_days($pmonth_days);

            /*
            // Dit jaar
            $year_days = [];
            for ($i = 0; $i < 31; $i++) {
                $year_days[] = date('Y-m-d', strtotime("-$i days"));
            }
            $result['this_year'] = $sum_days($year_days);

            // Vorig jaar
            $pyear_days = [];
            for ($i = 31; $i < 62; $i++) {
                $pyear_days[] = date('Y-m-d', strtotime("-$i days"));
            }
            $result['previous_year'] = $sum_days($pyear_days);
            */

            // --- Dit jaar (vanaf 1 januari t/m vandaag) ---
            $year_days = [];
            $first_day_this_year = strtotime('first day of January this year 00:00:00');
            $today = strtotime('today 00:00:00');
            for ($d = $first_day_this_year; $d <= $today; $d = strtotime('+1 day', $d)) {
                $year_days[] = date('Y-m-d', $d);
            }
            $result['this_year'] = $sum_days($year_days);


            // --- Vorig jaar (1 januari t/m 31 december) ---
            $pyear_days = [];
            $first_day_last_year = strtotime('first day of January last year 00:00:00');
            $last_day_last_year  = strtotime('last day of December last year 00:00:00');
            for ($d = $first_day_last_year; $d <= $last_day_last_year; $d = strtotime('+1 day', $d)) {
                $pyear_days[] = date('Y-m-d', $d);
            }
            $result['previous_year'] = $sum_days($pyear_days);


        }
    } catch (Exception $e) {
        error_log("Stats overview error: " . $e->getMessage());
    }

    echo json_encode($result);
    exit;
}

// ====================== STATISTIEKEN OVERZICHT ======================
if (isset($_GET['type']) && $_GET['type'] === 'stats_overview') {

    $result = [
        'today'           => ['cars' => 0, 'mpa' => 0],
        'yesterday'       => ['cars' => 0, 'mpa' => 0],
        'this_week'       => ['cars' => 0, 'mpa' => 0],
        'previous_week'   => ['cars' => 0, 'mpa' => 0],
        'this_month'      => ['cars' => 0, 'mpa' => 0],
        'previous_month'  => ['cars' => 0, 'mpa' => 0],
        'this_year'       => ['cars' => 0, 'mpa' => 0],
        'previous_year'   => ['cars' => 0, 'mpa' => 0]
    ];

    try {
        if (file_exists($db_path)) {
            $pdo = new PDO("sqlite:" . $db_path);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            $queries = [
                'today'          => "date(timestamp) = date('now', 'localtime')",
                'yesterday'      => "date(timestamp) = date('now', '-1 day', 'localtime')",
                'this_week'      => "strftime('%Y-%W', timestamp) = strftime('%Y-%W', 'now', 'localtime')",
                'previous_week'  => "strftime('%Y-%W', timestamp) = strftime('%Y-%W', 'now', '-7 days', 'localtime')",
                'this_month'     => "strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now', 'localtime')",
                'previous_month' => "strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now', '-1 month', 'localtime')",
                'this_year'      => "strftime('%Y', timestamp) = strftime('%Y', 'now', 'localtime')",
                'previous_year'  => "strftime('%Y', timestamp) = strftime('%Y', 'now', '-1 year', 'localtime')"
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

// Detector online status
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
