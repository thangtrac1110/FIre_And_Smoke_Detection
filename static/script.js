const ipUrlInput = document.getElementById("ip-url");
const btnIp = document.getElementById("btn-ip");
const btnWebcam = document.getElementById("btn-webcam");
const btnPublic = document.getElementById("btn-public");
const btnStop = document.getElementById("btn-stop");
const videoUpload = document.getElementById("video-upload");
const publicCameraUrlDisplay = document.getElementById("public-camera-url-display");
const viewportFrame = document.getElementById("viewport-frame");
const videoFeed = document.getElementById("video-feed");
const viewportPlaceholder = document.getElementById("viewport-placeholder");
const viewportLoading = document.getElementById("viewport-loading");
const modalOverlay = document.getElementById("modal-overlay");
const modalYes = document.getElementById("modal-yes");
const modalNo = document.getElementById("modal-no");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const headerStatusDot = document.getElementById("header-status-dot");
const headerStatusText = document.getElementById("header-status-text");
const confSlider = document.getElementById("conf-slider");
const iouSlider = document.getElementById("iou-slider");
const confValue = document.getElementById("conf-value");
const iouValue = document.getElementById("iou-value");
const metricFps = document.getElementById("metric-fps");
const metricTotal = document.getElementById("metric-total");
const metricConf = document.getElementById("metric-conf");
const metricClassCount = document.getElementById("metric-class-count");
const metricClasses = document.getElementById("metric-classes");

let metricsInterval = null;

confSlider.addEventListener("input", () => {
    confValue.textContent = parseFloat(confSlider.value).toFixed(2);
    fetch(`/update_params?conf=${confSlider.value}&iou=${iouSlider.value}`, { method: "POST" });
});

iouSlider.addEventListener("input", () => {
    iouValue.textContent = parseFloat(iouSlider.value).toFixed(2);
    fetch(`/update_params?conf=${confSlider.value}&iou=${iouSlider.value}`, { method: "POST" });
});

function startMetricsPolling() {
    stopMetricsPolling();
    metricsInterval = setInterval(fetchMetrics, 500);
}

function stopMetricsPolling() {
    if (metricsInterval !== null) {
        clearInterval(metricsInterval);
        metricsInterval = null;
    }
    metricFps.textContent = "0.0";
    metricTotal.textContent = "0";
    metricConf.textContent = "—";
    metricClassCount.textContent = "—";
    metricClasses.textContent = "—";
}

async function fetchMetrics() {
    try {
        const resp = await fetch("/metrics");
        const data = await resp.json();
        metricFps.textContent = data.fps;
        metricTotal.textContent = data.total_detections;
        metricConf.textContent = data.lowest_confidence > 0 ? data.lowest_confidence.toFixed(3) : "—";
        const classes = data.class_counts || {};
        const count = Object.keys(classes).length;
        metricClassCount.textContent = count > 0 ? count : "—";
        const classStr = Object.entries(classes).map(([k, v]) => `<span class="class-tag">${k}</span><span class="class-count">${v}</span>`).join(" ");
        metricClasses.innerHTML = classStr || "—";
    } catch {
        // ignore fetch errors during polling
    }
}

function getConfParam() {
    return parseFloat(confSlider.value).toFixed(2);
}

function getIouParam() {
    return parseFloat(iouSlider.value).toFixed(2);
}

function showLoading() {
    viewportLoading.classList.add("visible");
}

function hideLoading() {
    viewportLoading.classList.remove("visible");
}

function updateStatus(text, state) {
    statusText.textContent = text;
    statusDot.className = "status-dot";
    if (state === "active") {
        statusDot.classList.add("active");
        headerStatusDot.classList.add("live");
        headerStatusText.textContent = text;
    } else if (state === "error") {
        statusDot.classList.add("error");
        headerStatusDot.classList.remove("live");
        headerStatusText.textContent = text;
    } else {
        headerStatusDot.classList.remove("live");
        headerStatusText.textContent = "System idle";
    }
}

function showStream(url, sourceName) {
    if (videoFeed.src && videoFeed.src !== window.location.href) {
        fetch("/stop_stream", { method: "POST" });
        videoFeed.onload = null;
        videoFeed.onerror = null;
        videoFeed.src = "";
        stopMetricsPolling();
    }

    showLoading();
    viewportPlaceholder.style.display = "none";

    viewportFrame.classList.remove("active");

    videoFeed.onload = function () {
        hideLoading();
        viewportFrame.classList.add("active");
        updateStatus(sourceName, "active");
        startMetricsPolling();
    };

    videoFeed.onerror = function () {
        hideLoading();
        updateStatus("Connection lost", "error");
        stopMetricsPolling();
    };

    videoFeed.src = url;
}

function stopStream() {
    fetch("/stop_stream", { method: "POST" });
    videoFeed.src = "";
    videoFeed.onload = null;
    videoFeed.onerror = null;
    viewportFrame.classList.remove("active");
    viewportPlaceholder.style.display = "";
    hideLoading();
    updateStatus("Ready — select a source to begin", "");
    stopMetricsPolling();
}

function showModal() {
    modalOverlay.classList.add("visible");
}

function hideModal() {
    modalOverlay.classList.remove("visible");
}

function startWebcam() {
    showStream(`/video_feed?source=webcam&conf=${getConfParam()}&iou=${getIouParam()}`, "Local Webcam");
}

function disableButtons(disabled) {
    btnIp.disabled = disabled;
    btnWebcam.disabled = disabled;
    document.getElementById("btn-upload-label").style.pointerEvents = disabled ? "none" : "auto";
}

btnIp.addEventListener("click", async () => {
    const url = ipUrlInput.value.trim() || ipUrlInput.placeholder;
    disableButtons(true);
    showLoading();
    updateStatus("Connecting to IP camera…", "");

    try {
        const resp = await fetch(`/check_stream?url=${encodeURIComponent(url)}`);
        const data = await resp.json();

        if (data.success) {
            showStream(`/video_feed?source=ip&url=${encodeURIComponent(url)}&conf=${getConfParam()}&iou=${getIouParam()}`, "IP Camera");
        } else {
            hideLoading();
            updateStatus("IP camera unreachable", "error");
            showModal();
        }
    } catch {
        hideLoading();
        updateStatus("IP camera unreachable", "error");
        showModal();
    } finally {
        disableButtons(false);
    }
});

btnWebcam.addEventListener("click", () => {
    startWebcam();
});

btnPublic.addEventListener("click", () => {
    const url = publicCameraUrlDisplay ? publicCameraUrlDisplay.textContent.trim() : "";
    if (!url) {
        updateStatus("No public camera URL configured", "error");
        return;
    }
    showStream(`/video_feed?source=public&url=${encodeURIComponent(url)}&conf=${getConfParam()}&iou=${getIouParam()}`, "Public Camera");
});

btnStop.addEventListener("click", () => {
    stopStream();
});

videoUpload.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    disableButtons(true);
    showLoading();
    updateStatus("Uploading video…", "");

    const formData = new FormData();
    formData.append("video", file);

    try {
        const resp = await fetch("/upload", { method: "POST", body: formData });
        const data = await resp.json();

        if (data.filename) {
            showStream(`/video_feed?source=file&path=${encodeURIComponent(data.filename)}&conf=${getConfParam()}&iou=${getIouParam()}`, file.name);
        } else {
            hideLoading();
            updateStatus("Upload failed", "error");
        }
    } catch (err) {
        hideLoading();
        updateStatus("Upload failed", "error");
    } finally {
        disableButtons(false);
        videoUpload.value = "";
    }
});

modalYes.addEventListener("click", () => {
    hideModal();
    startWebcam();
});

modalNo.addEventListener("click", () => {
    hideModal();
});