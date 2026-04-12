// Laatste Detectie: foto + video
const latestDiv = document.getElementById('latest-detection');
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

// === LAATSTE DETECTIE: foto + video eronder ===
const latestDiv = document.getElementById('latest-detection');
const currentVideo = latestDiv.querySelector('video');   // check of er al een video speelt

if (data.latest_photo) {
    let html = `
        <img src="media/${data.latest_photo.url}" alt="Laatste foto" style="width:100%; border-radius:12px;">
        <p class="filename">${data.latest_photo.filename}</p>
    `;

    if (data.latest_video) {
        const videoUrl = `media/${data.latest_video.url}`;
        const isCurrentlyPlaying = currentVideo && !currentVideo.paused;

        // Als er al een video speelt van dezelfde file, laat hem dan met rust
        if (isCurrentlyPlaying && currentVideo.src.includes(data.latest_video.url)) {
            html += `
                <div style="margin-top: 20px;">
                    <p class="filename" style="margin-bottom:8px; color:#94a3b8;">Bijbehorende video:</p>
                    <!-- Laat de bestaande video zitten -->
                </div>
            `;
        } else {
            html += `
                <div style="margin-top: 20px;">
                    <p class="filename" style="margin-bottom:8px; color:#94a3b8;">Bijbehorende video:</p>
                    <video controls muted playsinline style="width:100%; border-radius:12px; max-height: 380px;">
                        <source src="${videoUrl}" type="video/mp4">
                    </video>
                    <p class="filename">${data.latest_video.filename}</p>
                </div>
            `;
        }
    }
    latestDiv.innerHTML = html;
}