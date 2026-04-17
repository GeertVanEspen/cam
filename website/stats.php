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
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            background: #1e2937;
            border-radius: 16px;
            overflow: hidden;
        }
        .stats-table th {
            background: #334155;
            padding: 16px 20px;
            text-align: left;
            font-weight: 600;
            color: #cbd5e1;
        }
        .stats-table td {
            padding: 14px 20px;
            border-bottom: 1px solid #334155;
        }
        .stats-table tr:last-child td {
            border-bottom: none;
        }
        .number {
            font-size: 1.35rem;
            font-weight: 700;
            color: #60a5fa;
            text-align: right;
        }
        .period {
            color: #e2e8f0;
            font-weight: 500;
        }
        .back-button {
            display: inline-block;
            margin-bottom: 25px;
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

        <table class="stats-table">
            <thead>
                <tr>
                    <th>Periode</th>
                    <th style="text-align:right;">Auto’s</th>
                    <th style="text-align:right;">MPA’s</th>
                </tr>
            </thead>
            <tbody id="stats-body">
                <!-- Wordt gevuld door JavaScript -->
            </tbody>
        </table>
    </div>

    <script src="script.js"></script>
    <script>
        function loadDailyStats() {
            fetch('api.php?type=stats_overview')
                .then(r => r.json())
                .then(data => {
                    const periods = [
                        { label: 'Vandaag',       key: 'today' },
                        { label: 'Gisteren',      key: 'yesterday' },
                        { label: 'Deze week',     key: 'this_week' },
                        { label: 'Vorige week',   key: 'previous_week' },
                        { label: 'Deze maand',    key: 'this_month' },
                        { label: 'Vorige maand',  key: 'previous_month' },
                        { label: 'Dit jaar',      key: 'this_year' },
                        { label: 'Vorig jaar',    key: 'previous_year' }
                    ];

                    let html = '';
                    periods.forEach(p => {
                        const s = data[p.key] || { cars: 0, mpa: 0 };
                        html += `
                            <tr>
                                <td class="period">${p.label}</td>
                                <td class="number">${s.cars}</td>
                                <td class="number">${s.mpa}</td>
                            </tr>
                        `;
                    });

                    document.getElementById('stats-body').innerHTML = html;
                })
                .catch(err => {
                    console.error(err);
                    document.getElementById('stats-body').innerHTML = 
                        '<tr><td colspan="3" style="text-align:center; color:#ef4444; padding:40px;">Kon statistieken niet ophalen.</td></tr>';
                });
        }

        loadDailyStats();
        setInterval(loadDailyStats, 30000);
    </script>
</body>
</html>
