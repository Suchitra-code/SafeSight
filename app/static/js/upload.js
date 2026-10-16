/**
 * SafeSight AI – Upload & Processing Controller
 * Handles drag-and-drop, media file preview, confidence thresholding,
 * AJAX uploads, and real-time video progress polling.
 */

let selectedFile = null;

document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const previewArea = document.getElementById("previewArea");
  const previewFileName = document.getElementById("previewFileName");
  const previewFileSize = document.getElementById("previewFileSize");
  const imgPreview = document.getElementById("imgPreview");
  const videoPreview = document.getElementById("videoPreview");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const confSlider = document.getElementById("confSlider");
  const confVal = document.getElementById("confVal");

  // Slider change
  if (confSlider && confVal) {
    confSlider.addEventListener("input", (e) => {
      confVal.innerText = `${Math.round(e.target.value * 100)}%`;
    });
  }

  // Click dropzone to open picker
  dropzone.addEventListener("click", () => fileInput.click());

  // Drag and drop events
  ["dragenter", "dragover"].forEach(evt => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(evt => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  removeFileBtn.addEventListener("click", () => {
    clearSelection();
  });

  function clearSelection() {
    selectedFile = null;
    fileInput.value = "";
    previewArea.style.display = "none";
    dropzone.style.display = "block";
    imgPreview.src = "";
    imgPreview.style.display = "none";
    videoPreview.src = "";
    videoPreview.style.display = "none";
    analyzeBtn.disabled = true;
  }

  function handleFileSelected(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    const validImageExts = ["jpg", "jpeg", "png"];
    const validVideoExts = ["mp4", "avi", "mov"];

    if (!validImageExts.includes(ext) && !validVideoExts.includes(ext)) {
      showToast(`Unsupported file format (.${ext}). Please select JPG, PNG, MP4, AVI, or MOV.`, "error");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      showToast("File exceeds the 25 MB size limit.", "error");
      return;
    }

    selectedFile = file;
    dropzone.style.display = "none";
    previewArea.style.display = "block";
    previewFileName.innerText = file.name;
    previewFileSize.innerText = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
    analyzeBtn.disabled = false;

    const fileUrl = URL.createObjectURL(file);
    if (validImageExts.includes(ext)) {
      imgPreview.src = fileUrl;
      imgPreview.style.display = "block";
      videoPreview.style.display = "none";
    } else {
      videoPreview.src = fileUrl;
      videoPreview.style.display = "block";
      imgPreview.style.display = "none";
    }
  }

  // Submit to Upload API
  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = "<span>⏳</span> Analyzing Media...";

    const cameraSelect = document.getElementById("cameraSelect");
    const camName = cameraSelect.value;
    const location = cameraSelect.options[cameraSelect.selectedIndex].getAttribute("data-zone") || "Main Facility";
    const confidence = confSlider.value;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("camera_name", camName);
    formData.append("location", location);
    formData.append("confidence", confidence);

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Upload failed");
      }

      if (data.status === "done") {
        showToast("Analysis complete! Redirecting...", "success");
        setTimeout(() => {
          window.location.href = `/result/${data.upload_id}`;
        }, 600);
      } else if (data.status === "processing") {
        // Video processing in background
        pollVideoProgress(data.upload_id);
      }
    } catch (err) {
      showToast(err.message, "error");
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = "<span>🔍</span> Analyze Safety";
    }
  });

  function pollVideoProgress(uploadId) {
    const progressSection = document.getElementById("progressSection");
    const progressStatus = document.getElementById("progressStatus");
    const progressPercent = document.getElementById("progressPercent");
    const progressBarFill = document.getElementById("progressBarFill");

    progressSection.style.display = "block";

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${uploadId}`);
        const pData = await res.json();

        const pct = pData.percent || 0;
        progressBarFill.style.width = `${pct}%`;
        progressPercent.innerText = `${pct}%`;
        progressStatus.innerText = pData.status || "Processing video...";

        if (pct >= 100 || pData.error) {
          clearInterval(pollInterval);
          if (pData.error) {
            showToast("Video processing encountered an error: " + pData.status, "error");
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = "<span>🔍</span> Analyze Safety";
          } else {
            showToast("Video analysis complete!", "success");
            setTimeout(() => {
              window.location.href = `/result/${uploadId}`;
            }, 800);
          }
        }
      } catch (e) {
        console.error("Progress polling error:", e);
      }
    }, 1000);
  }
});
