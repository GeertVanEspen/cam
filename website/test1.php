// ==================== STATS HANDLING ====================
function handle_stats_upload()
{
  global $log_bestand, $tijd;

  $log_regel = "[$tijd] stats upload ontvangen" . PHP_EOL;
  file_put_contents($log_bestand, $log_regel, FILE_APPEND);

  $daily_car_count = (int)($_POST['daily_car_count'] ?? 0);
  $daily_mpa_count = (int)($_POST['daily_mpa_count'] ?? 0);
  $current_fps     = (float)($_POST['current_fps'] ?? 0.0);
  $imageCtr        = (int)($_POST['imageCtr'] ?? 0);

  $db_path = "/home/wwwdata/mpa_stats.db";

  try
  {
    $pdo = new PDO("sqlite:" . $db_path);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // === 1. Nieuwe stats invoegen ===
    $stmt = $pdo->prepare("
      INSERT INTO mpa_stats
      (daily_car_count, daily_mpa_count, current_fps, imageCtr)
      VALUES (:cars, :mpa, :fps, :imgctr)
    ");

    $stmt->execute([
      ':cars'    => $daily_car_count,
      ':mpa'     => $daily_mpa_count,
      ':fps'     => $current_fps,
      ':imgctr'  => $imageCtr
    ]);

    // === 2. Opruimen: verwijder records ouder dan 1 jaar ===
    $pdo->exec("
      DELETE FROM mpa_stats
      WHERE timestamp < datetime('now', '-1 year', 'localtime')
    ");

    $deleted = $pdo->query("SELECT changes()")->fetchColumn();

    $log_regel = "[$tijd] stats opgeslagen in DB: cars=$daily_car_count, mpa=$daily_mpa_count, fps=$current_fps";
    if ($deleted > 0)
    {
      $log_regel .= " | $deleted oude records opgeruimd (ouder dan 1 jaar)";
    }
    $log_regel .= PHP_EOL;

    file_put_contents($log_bestand, $log_regel, FILE_APPEND);

    echo json_encode([
      'status' => 'success',
      'message' => 'Statistics saved to database'
    ]);

  }
  catch (Exception $e)
  {
    $log_regel = "[$tijd] DB error: " . $e->getMessage() . PHP_EOL;
    file_put_contents($log_bestand, $log_regel, FILE_APPEND);
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Database error']);
  }
}
