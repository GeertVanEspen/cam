<?php
// DEBUG (indien nodig)
// echo "<pre>";
// print_r($_GET);
// echo "</pre>";
logger("Incoming request: " . json_encode($_GET));
$ref = isset($_GET['ref']) ? $_GET['ref'] : '';


$token = $_GET['token'] ?? '';
$hash = md5($token);
$actionMode = false;
$actionResponse = '';

//logger("token:$token");
//logger("hash:$hash");

if ($hash !== "464e2d3818a66de7c1f111b7ea86492d") {
    http_response_code(403);
    echo "403 Forbidden";
    exit;
}


$actionResult = '';

if (isset($_GET['action']) && $_GET['action'] === 'startsessie') {
    $actionMode = true;
    $context = stream_context_create([
        'http' => ['timeout' => 3]
    ]);

    $tijd  = date("Y-m-d H:i:s");
    $smsServerResponse = "empty";
    // Code to send SMS.
    //$smsServerResponse = file_get_contents("http://arduino/arduino/sms/0486565750%0AAN36E%202FUT768");
    $smsServerResponse = file_get_contents("http://arduino/arduino/sms/4411%0AAN36E%202FUT768");
    //$smsServerResponse = "done!";
    $smsServerResponse = str_replace("\n", "", $smsServerResponse);

    $tijd  = date("Y-m-d H:i:s");

    if ($smsServerResponse == "done!") {
        $actionResponse = $smsServerResponse;
    } else {
        $actionResponse = "not sent!";
    }
    logger("Arduino response:$smsServerResponse");
}

// Datum en tijd uit ref halen (formaat: jjjjmmdd_hhmmss)
$formattedDate = "Onbekend";
if ($ref && preg_match('/(\d{8})_(\d{6})/', $ref, $matches)) {
    $date = $matches[1];
    $time = $matches[2];

    $formattedDate = substr($date, 6, 2) . "-" . substr($date, 4, 2) . "-" . substr($date, 0, 4)
        . " " .
        substr($time, 0, 2) . ":" . substr($time, 2, 2) . ":" . substr($time, 4, 2);
}

// Bestanden
$imagePath = __DIR__ . "/media/" . $ref . ".jpg";
$imageUrl  = "media/" . $ref . ".jpg";

$videoPath = __DIR__ . "/media/" . $ref . ".mp4";
$videoUrl  = "media/" . $ref . ".mp4";

$videoExists = file_exists($videoPath);



function logger($message) {
    $logFile = "/home/wwwdata/actie_ntfy.log";
    $maxSize = 10 * 1024 * 1024; // 10 MB

    // Als bestand bestaat en te groot is  verwijderen
    if (file_exists($logFile) && filesize($logFile) > $maxSize) {
        unlink($logFile);
    }

    // Datum + tijd
    $timestamp = date("Y-m-d H:i:s");

    // Logregel
    $line = "[" . $timestamp . "] " . $message . PHP_EOL;

    // Schrijf naar bestand
    file_put_contents($logFile, $line, FILE_APPEND | LOCK_EX);
}

?>

<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MPA auto gedetecteerd</title>

<?php if (!$videoExists): ?>
<meta http-equiv="refresh" content="15">
<?php endif; ?>

<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    background-color: #f2f2f7;
    margin: 0;
    padding: 0;
    text-align: center;
}

.container {
    padding: 20px;
}

.card {
    background: white;
    border-radius: 16px;
    padding: 15px;
    margin: 10px;
}

h1 {
    font-size: 24px;
    margin-bottom: 10px;
}

.timestamp {
    font-size: 16px;
    color: #555;
    margin-bottom: 20px;
}

img, video {
    max-width: 100%;
    height: auto;
    border-radius: 12px;
    margin-bottom: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
}

.action-btn {
    margin-top: 20px;
    padding: 14px 20px;
    font-size: 16px;
    border: none;
    border-radius: 12px;
    background-color: #007aff;
    color: white;
    width: 100%;
    max-width: 300px;
}

.action-btn:active {
    background-color: #005ecb;
}
</style>
</head>

<body>
<div class="container">
    <div class="card">
    <?php if ($actionMode): ?>
        <h1>SMS verstuurd</h1>

        <?php if ($actionResponse == "done!"): ?>
            <p>✅ Resultaat om <?php echo htmlspecialchars($tijd); ?>:</p>
            <p><?php echo htmlspecialchars($actionResponse); ?></p>
            <p>Zoek in de 4411 app naar de huidige sessie, vergeet niet ze te stoppen!</p>
        <?php else: ?>
            <p>Resultaat om <?php echo htmlspecialchars($tijd); ?>:</p>
            <p><?php echo htmlspecialchars($actionResponse); ?></p>
            <p>Fout bij versturen, gelieve zelf een sessie te starten.</p>
        <?php endif; ?>

        <!--button onclick="closeTab()" class="action-btn">Sluiten</button-->


        <button onclick="goBack()" class="action-btn">Terug</button>

        <script>
        function goBack() {
            window.history.back();
        }
        </script>


    <?php else: ?>
        <h1>🚗 MPA auto gedetecteerd</h1>
        <div class="timestamp"><?php echo htmlspecialchars($formattedDate); ?></div>

        <?php if (file_exists($imagePath)): ?>
            <img src="<?php echo htmlspecialchars($imageUrl); ?>">
        <?php else: ?>
            <p>Afbeelding niet gevonden.</p>
        <?php endif; ?>

        <?php if ($videoExists): ?>
            <video controls autoplay muted playsinline>
                <source src="<?php echo htmlspecialchars($videoUrl); ?>" type="video/mp4">
                Je browser ondersteunt geen video.
            </video>
        <?php else: ?>
            <p>🎥 video komt zo...</p>
        <?php endif; ?>

        <form method="get">
            <input type="hidden" name="ref" value="<?php echo htmlspecialchars($ref); ?>">
            <input type="hidden" name="token" value="<?php echo htmlspecialchars($_GET['token'] ?? ''); ?>">
            <input type="hidden" name="action" value="startsessie">

            <button type="submit" class="action-btn">Start sessie...</button>
        </form>
    <?php endif; ?>
    </div>
</div>
</body>
</html>
