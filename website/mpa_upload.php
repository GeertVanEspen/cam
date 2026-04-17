<?php

date_default_timezone_set('Europe/Brussels');

$log_bestand   = "/home/wwwdata/mpa_upload.log";
$tijd          = date("Y-m-d H:i:s");
$upload_dir_photos = './media/';
$upload_dir_videos = './media/';

// Logbestand opruimen als te groot
$fsize = filesize($log_bestand) ?: 0;
if ($fsize > 200000)
{
  unlink($log_bestand);
}

// Basis logging.
$log_regel = "[$tijd] mpa_upload.php triggered | IP: " . ($_SERVER['REMOTE_ADDR'] ?? 'unknown') . PHP_EOL;
file_put_contents($log_bestand, $log_regel, FILE_APPEND);

// Token Controle
// We checken of 'token' in de URL staat.
if (!isset($_POST['token']))
{
  $log_regel = "[$tijd] token ontbreekt" . PHP_EOL;
  file_put_contents($log_bestand, $log_regel, FILE_APPEND);
  // Geen token? Geef een 403 Forbidden en stop direct.
  header('HTTP/1.1 403 Forbidden');
  exit("Geen toegang");
}
else
{
  $token = $_POST['token'] ?? '';
}

$hash  = md5($token);

if ($hash !== "8071816ed8087376ed378f15a94ed306")
{
  $log_regel = "[$tijd] token ongeldig ($hash)" . PHP_EOL;
  file_put_contents($log_bestand, $log_regel, FILE_APPEND);
  // Fout token? Geef een 403 Forbidden en stop direct.
  header('HTTP/1.1 403 Forbidden');
  exit("Geen toegang.");
}


////////////////////
// ====================== TYPE BEPALEN ======================
$type = $_POST['type'] ?? ''; // 'photo', 'video', 'stats', 'log' of 'check_meldingen'

if ($type === 'check_meldingen')
{
  // Nieuwe check: retourneert alleen of meldingen aan staan
  $meldingen_aan = !file_exists('/home/wwwdata/melding.uit');

  echo json_encode([
    'status' => 'success',
    'meldingen_aan' => $meldingen_aan
  ]);
  exit;   // stop hier, geen verdere verwerking
}

if (!in_array($type, ['photo', 'video', 'stats', 'log']))
{
  http_response_code(400);
  die('Invalid type');
}

if ($type === 'stats')
{
  // ==================== STATS HANDLING ====================
  handle_stats_upload();
  exit;
}

// ====================== REMOTE LOGGING ======================
if ($type === 'log')
{
  $message = $_POST['message'] ?? '';

  if (empty($message))
  {
    http_response_code(400);
    echo json_encode(['status' => 'error', 'message' => 'No message provided']);
    exit;
  }

  $log_regel = "[$tijd] " . trim($message) . PHP_EOL;
  file_put_contents($log_bestand, $log_regel, FILE_APPEND);

  echo json_encode([
    'status' => 'success',
    'message' => 'Log entry added'
  ]);
  exit;
}

$upload_dir = ($type === 'photo') ? $upload_dir_photos : $upload_dir_videos;

/*
$log_regel = "[$tijd] token:$token" . PHP_EOL;
file_put_contents($log_bestand, $log_regel, FILE_APPEND);

$log_regel = "[$tijd] hash:$hash" . PHP_EOL;
file_put_contents($log_bestand, $log_regel, FILE_APPEND);
*/

$tijd  = date("Y-m-d H:i:s");

if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK)
{
  http_response_code(400);
  die('No file or upload error');
}

////////////////////////////////
// Eerst opkuisen.
$directoryPath = './media';
$daysOld = 5;
$secondsOld = $daysOld * 24 * 60 * 60;
$now = time();

$dir = new DirectoryIterator($directoryPath);
foreach ($dir as $fileinfo)
{
  // Sla mappen en 'parent' pointers (.. en .) over
  if (!$fileinfo->isDot() && $fileinfo->isFile())
  {
    $extension = strtolower($fileinfo->getExtension());
    $filePath = $fileinfo->getPathname();

    // Controleer of het een .mp4 of .jpg is
    if (in_array($extension, ['mp4', 'jpg', 'jpeg']))
    {
      if (($now - $fileinfo->getMTime()) >= $secondsOld)
      {
        unlink($filePath);
      }
    }
  }
}
////////////////////////////////

$file = $_FILES['file'];

// Originele naam zoals bekend in Python
$original_name = basename($file['name']);

// === Gebruik originele bestandsnaam (die al timestamp bevat) maar maak hem veilig ===
$original_filename = pathinfo($original_name, PATHINFO_FILENAME);  // "event_20260331_092145_camper1" zonder extensie
$ext = strtolower(pathinfo($original_name, PATHINFO_EXTENSION));   // "jpg" of "mp4"

// Maak een nette, veilige bestandsnaam.
// Voorbeeld resultaat: motion_20260331_092145.jpg
$safe_name = $original_filename . '.' . $ext;
$destination = $upload_dir . $safe_name;

// Verplaats het bestand.
if (move_uploaded_file($file['tmp_name'], $destination))
{
  $log_regel = "[$tijd] $type uploaded: $safe_name" . PHP_EOL;
  file_put_contents($log_bestand, $log_regel, FILE_APPEND);

  echo json_encode([
    'status' => 'success',
    'filename' => $safe_name,
    'message' => "$type uploaded successfully"
  ]);
}
else
{
  http_response_code(500);
  echo json_encode(['status' => 'error', 'message' => 'Failed to save file']);
}

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

?>
