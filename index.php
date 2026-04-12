<?php
/*

PHP file to be placed on MPA parking server.
Shows recent MPA-hits, video archives and more information.

*/
date_default_timezone_set('Europe/Brussels');

$triggerFile = 'C:/cam/record.on';
$notifOffFile = 'C:/cam/melding.off'; // Het nieuwe bestandje
$restartFile = 'C:/cam/restart.trigger'; // Restart trigger bestand
$logFile = 'C:/cam/MPA_Detect_inspector.log';
$imgDir = 'C:/inetpub/wwwroot/ntfy/';
$statusFile = 'C:/inetpub/wwwroot/ntfy/status.json';
$delay_minutes = 0;
$inspecteur_status = "Offline";
$dot_color = "#e74c3c"; // Rood standaard

if (file_exists($statusFile)) {
    $content = file_get_contents($statusFile);

    // Verwijder eventuele BOM-tekens handmatig (voor de zekerheid)
    $content = str_replace("\xEF\xBB\xBF", '', $content);

    $statusData = json_decode($content, true);

    // Controleer of de JSON succesvol is geladen en de keys bestaan
    if ($statusData && isset($statusData['last_run']) && isset($statusData['delay'])) {
        $last_run = strtotime($statusData['last_run']);
        $delay_minutes = (int)$statusData['delay'];

        // Check of de status.json niet ouder is dan 5 minuten (300 sec)
        if ((time() - $last_run) < 300) {
            $inspecteur_status = ($delay_minutes > 5) ? "Vertraagd" : "Online";
            $dot_color = ($delay_minutes > 5) ? "#f1c40f" : "#2ecc71";
        }
    }
}

// Acties verwerken
if (isset($_GET['action'])) {
    if ($_GET['action'] == 'rec_on') file_put_contents($triggerFile, 'ON');
    if ($_GET['action'] == 'rec_off') if (file_exists($triggerFile)) unlink($triggerFile);

    if ($_GET['action'] == 'notif_off') file_put_contents($notifOffFile, 'OFF');
    if ($_GET['action'] == 'notif_on') if (file_exists($notifOffFile)) unlink($notifOffFile);

    if ($_GET['action'] == 'restart') {
            file_put_contents($restartFile, 'RESTART');
            //shell_exec("schtasks /run /tn \"MPA_Detect_Daily\"");
            header("Location: index.php?restarting=1");
            exit;
        }

    header("Location: index.php");
    exit;
}

$recording = file_exists($triggerFile);
$notificationsActive = !file_exists($notifOffFile); // Active als het bestand er NIET is


// LOG BESTAND LEZEN.
$lastLogs = "";
if (file_exists($logFile)) {
    $lines = @file($logFile);
    // Neem de laatste 10 regels
    $last10 = array_slice($lines, -10);
    $lastLogs = implode("", $last10);
} else {
    $lastLogs = "Logbestand niet gevonden op: " . $logFile;
}






// Haal de 3 laatste JPG's op
$images = glob($imgDir . "*.jpg");
array_multisort(array_map('filemtime', $images), SORT_DESC, $images);
$latestImages = array_slice($images, 0, 3);
?>

<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60"> <title>MPA Control Panel</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #e1e1e1; text-align: center; padding: 20px; }
        .grid-buttons { display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; }
        .clock-box { font-size: 0.9em; color: #4ecca3; margin-bottom: 10px; }
        .refresh-info { font-size: 0.8em; color: #95a5a6; margin-top: 10px; }
        .container { max-width: 900px; margin: auto; }
        .card { background: #16213e; padding: 25px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 20px; border: 1px solid #0f3460; }
        .status-box { font-size: 1.2em; padding: 15px; border-radius: 8px; margin-bottom: 20px; background: #0f3460; }
        .btn { padding: 12px 25px; border: none; border-radius: 5px; cursor: pointer; font-size: 1em; text-decoration: none; color: white; display: inline-block; transition: 0.3s; }
        .btn-on { background: #27ae60; } .btn-on:hover { background: #2ecc71; }
        .btn-off { background: #e74c3c; } .btn-off:hover { background: #ff7675; }
        .thumb-container { display: flex; justify-content: center; gap: 15px; margin-top: 20px; flex-wrap: wrap; }
        .thumb-card { background: #0f3460; padding: 10px; border-radius: 8px; width: 250px; }
        .thumb-card img { width: 100%; border-radius: 5px; border: 1px solid #16213e; }
        pre { text-align: left; background: #000; padding: 15px; font-size: 0.85em; color: #00ff00; border-radius: 5px; overflow-x: auto; border: 1px solid #0f3460; }
        a { color: #4ecca3; text-decoration: none; }
    </style>

    <script>
        function updateClock() {
            const now = new Date();
            const clockElement = document.getElementById('clock');
            if (clockElement) {
                clockElement.innerHTML = now.toLocaleTimeString('nl-BE');
            }

            // URL OPSCHONEN:
            // Als 'restarting=1' in de URL staat, halen we het weg zonder te herladen.
            if (window.location.search.indexOf('restarting=1') > -1) {
                const newUrl = window.location.pathname;
                window.history.replaceState({}, document.title, newUrl);

                // Verberg de tekst visueel na 10 seconden (optioneel)
                setTimeout(function() {
                    const alertMsg = document.getElementById('restart-alert');
                    if (alertMsg) alertMsg.style.opacity = '0';
                    // Gebruik opacity voor een zachte overgang als je wilt
                }, 10000);
            }
        }

        // Start de klok en de URL-check elke seconde
        setInterval(updateClock, 1000);

        // Roep het ook direct één keer aan bij laden
        window.addEventListener('load', updateClock);
    </script>

    <!--script>
        // Voeg dit toe aan je updateClock functie of apart in de script tag
        window.onload = function() {
            updateClock(); // Bestaande aanroep

            // Verwijder de 'restarting' parameter uit de URL zonder te herladen
            if (window.location.search.indexOf('restarting=1') > -1) {
                const newUrl = window.location.pathname;
                window.history.replaceState({}, document.title, newUrl);
            }
        }

        function updateClock() {
            const now = new Date();
            document.getElementById('clock').innerHTML = now.toLocaleTimeString('nl-BE');
        }

        setInterval(updateClock, 1000);

    </script-->
</head>
<body onload="updateClock()">
    <div class="container">
        <div class="card">
            <div class="clock-box">Server tijd: <span id="clock">--:--:--</span></div>

            <div class="delay-indicator">
                <span class="dot" style="background-color: <?php echo $dot_color; ?>"></span>
                Inspecteur: <?php echo $inspecteur_status; ?> (<?php echo $delay_minutes; ?>m)
            </div>

            <h1>🛡️ MPA Inspecteur v3.0</h1>

            <div class="delay-indicator">
                <span class="dot" style="background-color: <?php echo $dot_color; ?>"></span>
                Inspecteur: <?php echo $inspecteur_status; ?>
                <?php if($inspecteur_status != "Offline") echo "($delay_minutes min achterstand)"; ?>
            </div>

            <div class="status-box">
                Video: <?php echo $recording ? '<b style="color:#2ecc71">🔴 OPNAME</b>' : '<b style="color:#95a5a6">⚪ DETECTIE</b>'; ?> |
                Meldingen: <?php echo $notificationsActive ? '<b style="color:#2ecc71">🔔 AAN</b>' : '<b style="color:#e74c3c">🔕 UIT</b>'; ?>
            </div>

            <div class="grid-buttons">
                <a href="?action=<?php echo $recording ? 'rec_off' : 'rec_on'; ?>" class="btn <?php echo $recording ? 'btn-off' : 'btn-on'; ?>">
                    <?php echo $recording ? 'Stop Recording' : 'Start Recording'; ?>
                </a>

                <a href="?action=<?php echo $notificationsActive ? 'notif_off' : 'notif_on'; ?>" class="btn <?php echo $notificationsActive ? 'btn-off' : 'btn-on'; ?>">
                    <?php echo $notificationsActive ? 'Stop Meldingen' : 'Start Meldingen'; ?>
                </a>
            </div>

            <div class="grid-buttons" style="margin-top: 10px;">
                <a href="?action=restart" class="btn" style="background: #6c5ce7; font-size: 0.8em;" onclick="return confirm('Inspecteur herstarten?')">
                    🔄 Herstart Inspecteur (PS1)
                </a>
            </div>

            <?php if(isset($_GET['restarting'])): ?>
                <p id="restart-alert" style="color: #f1c40f; font-size: 0.8em;">Herstart commando verzonden. Even geduld...</p>
            <?php endif; ?>

            <div class="refresh-info">
                Laatst ververst op: <?php echo date('H:i:s'); ?>
                <a href="index.php" style="margin-left:10px; border:1px solid #4ecca3; padding:2px 8px; border-radius:3px;">Ververs nu</a>
            </div>
        </div>

        <div class="card">
            <h3>📸 Laatste Detecties</h3>
            <div class="thumb-container">
                <?php if(empty($latestImages)): ?>
                    <p>Nog geen beelden gevonden.</p>
                <?php else: ?>
                    <?php foreach ($latestImages as $img): $name = basename($img); ?>
                        <div class="thumb-card">
                            <a href="/ntfy/<?php echo $name; ?>" target="_blank">
                                <img src="/ntfy/<?php echo $name; ?>" alt="Detectie">
                            </a>
                            <p style="font-size: 0.7em; margin-top: 5px;"><?php echo $name; ?></p>
                        </div>
                    <?php endforeach; ?>
                <?php endif; ?>
            </div>
            <p><a href="/ntfy/">Open volledige archief &rarr;</a></p>
        </div>

        <div class="card">
            <h3>📜 Systeem Log (PowerShell)</h3>
            <pre><?php echo htmlspecialchars($lastLogs); ?></pre>
        </div>
    </div>
</body>
</html>
