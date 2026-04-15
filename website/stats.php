<?php
// website/stats.php
date_default_timezone_set('Europe/Brussels');
?>
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPA Detector - Statistieken</title>
    <link rel="stylesheet" href="style.css">
    <style>
        .stats-container {
            max-width: 960px;
            margin: 0 auto;
            padding: 20px;
        }
        .period-card {
            background: #1e2937;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .period-title {
            font-size: 1.25rem;
            color: #cbd5e1;
            margin-bottom: 16px;
            border-bottom: 1px solid #334155;
            padding-bottom: 10px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 0;
            border-bottom: 1px solid #334155;
        }
        .stat-row:last-child {
            border-bottom: none;
        }
        .stat-label {
            font-size: 1.1rem;
            color: #e2e8f0;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #60a5fa;
        }
        .back-button {
            display: inline-block;
            margin: 20px 0 30px 0;
            padding: 12px 28px;
            background: #3b82f6;
            color: white;
            text-decoration: none;
            border-radius: 9999px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="stats-container">
        <a href="index.php" class="back-button">← Terug naar Dashboard</a>
        
        <h1 style="text-align:center; margin-bottom:30px;">📊 Statistieken</h1>

        <div id="stats-content">
            <!-- Wordt dynamisch gevuld door JavaScript -->
        </div>
    </div>

    <script src="script.js"></script>
    <script>
        function loadDailyStats() {
            fetch('api.php?type=stats_overview')
                .then(r => r.json())
                .then(data => {
                    let html = '';

                    const periods = [
                        { title: 'Vandaag',      key: 'today' },
                        { title: 'Gisteren',     key: 'yesterday' },
                        { title: 'Deze week',    key: 'this_week' },
                        { title: 'Deze maand',   key: 'this_month' }
                    ];

                    periods.forEach(p => {
                        const s = data[p.key] || { cars: 0, mpa: 0 };
                        html += `
                            <div class="period-card">
                                <div class="period-title">${p.title}</div>
                                <div class="stat-row">
                                    <span class="stat-label">🚗 Auto's</span>
                                    <span class="stat-value">${s.cars}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">🚨 MPA</span>
                                    <span class="stat-value">${s.mpa}</span>
                                </div>
                            </div>
                        `;
                    });

                    document.getElementById('stats-content').innerHTML = html;
                })
                .catch(err => {
                    console.error(err);
                    document.getElementById('stats-content').innerHTML = 
                        '<p style="color:#ef4444; text-align:center; padding:40px;">Kon statistieken niet ophalen.</p>';
                });
        }

        // Laad bij openen en ververs elke 30 seconden
        loadDailyStats();
        setInterval(loadDailyStats, 30000);
    </script>
</body>
</html>
