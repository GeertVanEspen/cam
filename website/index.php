<?php
date_default_timezone_set('Europe/Brussels');
$title = "MPA Detector v1.0";
?>
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $title ?></title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header style="margin-bottom: 20px;">
            <h1 style="margin: 0 0 10px 0;">🚗 MPA Detector <span class="version">v1.0</span></h1>

            <div style="display: flex; justify-content: space-between; align-items: flex-end;">

                <div>
                    <div id="server-time" class="server-time">Server tijd: --:--:--</div>
                    <div id="status" class="status">
                        Detector: <span id="detector-status">Offline</span>
                    </div>
                </div>

                <div>
                    <a href="../index.html" style="text-decoration: none;">
                        <button style="padding: 8px 14px; background: #ffffff; color: #1a1a1a; border: 1px solid #ccc; border-radius: 8px; cursor: pointer; font-weight: bold; display: flex; align-items: center; gap: 5px;">
                            <span>&#10229;</span> Terug
                        </button>
                    </a>
                </div>

            </div>
        </header>

        <!-- Statistieken knop naast meldingen -->
        <div class="card" style="display:flex; gap:15px;">
            <div style="flex:1;">
                <!--h2>Meldingen</h2-->
                <div class="toggle-container">
                    <button id="toggle-meldingen" class="toggle-btn">
                        <span id="toggle-text">Meldingen AAN</span>
                    </button>
                </div>
            </div>
            <div style="flex:1; display:flex; align-items:center;">
                <a href="stats.php" style="text-decoration:none; width:100%;">
                    <button style="width:100%; padding:12px; font-size:0.85rem; background:#3b82f6; color:white; border:none; border-radius:12px;">
                        📊 Statistieken
                    </button>
                </a>
            </div>
        </div>

        <!-- Statistieken -->
        <div class="card">
            <h2>Statistieken sinds 9u00</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">🚗</div>
                    <div class="stat-value" id="car-count">0</div>
                    <div class="stat-label">Auto's</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🚨</div>
                    <div class="stat-value" id="mpa-count">0</div>
                    <div class="stat-label">MPA</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📸</div>
                    <div class="stat-value" id="fps-value">0.0</div>
                    <div class="stat-label">FPS</div>
                </div>
            </div>
        </div>

        <!-- Laatste Detectie -->
        <div class="card">
            <h2>Laatste Detectie</h2>
            <div id="latest-detection" class="latest-detection"></div>
        </div>

        <!-- Recente Detecties -->
        <div class="card">
            <h2>Recente Detecties</h2>
            <div id="recent-grid" class="recent-grid"></div>
        </div>

        <!-- Systeem Log -->
        <div class="card">
            <h2>Systeem Log</h2>
            <pre id="system-log" class="log"></pre>
        </div>

        <footer>
            <button onclick="refreshAll()" class="refresh-btn">Ververs nu</button>
            <div id="last-updated" class="last-updated">Laatst ververst: nooit</div>
        </footer>
    </div>

    <script src="script.js"></script>
</body>
</html>
