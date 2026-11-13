"use strict";
window.gdo.video = {
    gdo_init: function() {
    },
};

// The status endpoint exposes only whether the encoder is producing frames.
// Keep this independent of viewer authentication and do not start the stream.
function updateVideoStreamLink() {
    const link = document.querySelector('[data-video-stream-status]');
    if (!link) return;
    const update = () => fetch(link.dataset.videoStreamStatus, {cache: 'no-store'})
        .then(response => link.classList.toggle('video-stream-live', response.ok))
        .catch(() => link.classList.remove('video-stream-live'));
    update();
    setInterval(update, 15000);
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateVideoStreamLink, {once: true});
} else {
    updateVideoStreamLink();
}
