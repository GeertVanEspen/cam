// script.js - Met debug voor Detector status

let lastUpdated = '';
let isCurrentlyPlaying = false;

function updateServerTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('nl-NL', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('server-time').textContent = `Server tijd: ${timeStr}`;
}

function refreshAll() {
    var lDetect = document.getElementById('latest-detection');
    var cVideo = lDetect.querySelector('video');

    isCurrentlyPlaying = cVideo && !cVideo.paused;
    if (isCurrentlyPlaying) return;

    fetch('api.php')
        .then(response => response.json())
        .then(data => {
            // Statistieken
            document.getElementById('car-count').textContent = data.stats.car_count;
            document.getElementById('mpa-count').textContent = data.stats.mpa_count;
            document.getElementById('fps-value').textContent = data.stats.fps;

            // Meldingen toggle
            const toggleBtn = document.getElementById('toggle-meldingen');
            const isAan = data.meldingen_aan;
            toggleBtn.classList.toggle('on', isAan);
            toggleBtn.classList.toggle('off', !isAan);
            document.getElementById('toggle-text').textContent = isAan ? 'Meldingen AAN' : 'Meldingen UIT';

            // === DETECTOR STATUS (met debug info) ===
            const statusEl = document.getElementById('detector-status');
            statusEl.textContent = data.detector_status_text;

            // Visuele status (groen/rood)
            const statusDiv = document.getElementById('status');
            if (data.detector_online) {
                statusDiv.classList.add('online');
                statusDiv.classList.remove('offline');
            } else {
                statusDiv.classList.add('offline');
                statusDiv.classList.remove('online');
            }

            // Laatste Detectie: foto + video
            const latestDiv = document.getElementById('latest-detection');
            const currentVideo = latestDiv.querySelector('video');   // check of er al een video speelt
            latestDiv.innerHTML = '';

            if (data.latest_photo) {
                let html = `
                    <img src="media/${data.latest_photo.url}" alt="Laatste foto" style="width:100%; border-radius:12px;">
                    <p class="filename">${data.latest_photo.filename}</p>
                `;

                if (data.latest_video) {
                    html += `
                        <div style="margin-top: 20px;">
                            <p class="filename" style="margin-bottom:8px; color:#94a3b8;">Bijbehorende video:</p>
                            <video controls muted playsinline style="width:100%; border-radius:12px; max-height: 380px;">
                                <source src="media/${data.latest_video.url}" type="video/mp4">
                            </video>
                            <p class="filename">${data.latest_video.filename}</p>
                        </div>
                    `;
                }
                latestDiv.innerHTML = html;
            }

            // Recente foto's (start vanaf de 2e, dus geen duplicaat van de grote foto)
            const grid = document.getElementById('recent-grid');
            grid.innerHTML = '';
            // Neem max 3 foto's, maar sla de eerste over (want dat is de grote foto)
            const recentToShow = data.recent_photos.slice(1, 4);   // index 1, 2, 3 → 2e, 3e, 4e foto

            recentToShow.forEach(filename => {
                const img = document.createElement('img');
                img.src = `media/${filename}`;
                img.style.cssText = "width:100%; border-radius:10px;";
                img.onclick = () => window.open(`media/${filename}`, '_blank');
                grid.appendChild(img);
            });

            // Systeem Log
            document.getElementById('system-log').textContent = data.log_lines.join('\n');

            // Laatst ververst
            const now = new Date();
            lastUpdated = now.toLocaleTimeString('nl-NL');
            document.getElementById('last-updated').textContent = `Laatst ververst: ${lastUpdated}`;

        })
        .catch(err => console.error('Fetch error:', err));
}

// Meldingen toggle
/*
document.getElementById('toggle-meldingen').addEventListener('click', () => {
    fetch('api.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'action=toggle_meldingen'
    }).then(() => refreshAll());
});*/

// Meldingen toggle (beveiligd via admin map)
document.getElementById('toggle-meldingen').addEventListener('click', () => {
    // Open de beveiligde pagina in een nieuw tabblad (of hetzelfde tabblad)
    window.location.href = 'admin/toggle_melding.php';
});

// Start
updateServerTime();
setInterval(updateServerTime, 1000);
refreshAll();
setInterval(refreshAll, 7000);
