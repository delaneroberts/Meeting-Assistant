// DOM elements


const uploadForm = document.getElementById("uploadForm");
const audioFileInput = document.getElementById("audioFile");
const processBtn = document.getElementById("processBtn");
const openTranscriptsBtn = document.getElementById("openTranscriptsBtn");

const progressSection = document.getElementById("progressSection");
const progressBar = document.getElementById("progressBar");
const progressLabel = document.getElementById("progressLabel");
const progressPercent = document.getElementById("progressPercent");

const errorBox = document.getElementById("errorBox");

const resultsSection = document.getElementById("resultsSection");
const summaryText = document.getElementById("summaryText");
const actionItemsList = document.getElementById("actionItemsList");
const transcriptText = document.getElementById("transcriptText");
const transcriptFileInfo = document.getElementById("transcriptFileInfo");

// Post-processing actions (PDF / discard)
const postActions = document.getElementById("postActions");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");
const discardBtn = document.getElementById("discardBtn");


// Live recording elements
const recordBtn = document.getElementById("recordBtn");
const pauseBtn = document.getElementById("pauseBtn");
const stopBtn = document.getElementById("stopBtn");
const liveStatus = document.getElementById("liveStatus");

// ---- General UI helpers ----

function resetUI() {
  errorBox.style.display = "none";
  errorBox.textContent = "";

  progressSection.style.display = "none";
  progressBar.style.width = "0%";
  progressPercent.textContent = "0%";
  progressLabel.textContent = "Starting…";

  resultsSection.style.display = "none";
  summaryText.textContent = "";
  actionItemsList.innerHTML = "";
  transcriptText.textContent = "";
  transcriptFileInfo.textContent = "";
  // Hide post actions
  if (postActions) postActions.style.display = "none";
  if (downloadPdfBtn) downloadPdfBtn.href = "#";
  if (discardBtn) discardBtn.onclick = null;
}

function showError(message) {
  errorBox.style.display = "block";
  errorBox.textContent = message || "An unknown error occurred.";
}

function setProgress(percent, label) {
  progressSection.style.display = "block";
  progressBar.style.width = `${percent}%`;
  progressPercent.textContent = `${percent}%`;
  if (label) {
    progressLabel.textContent = label;
  }
}

// ---- Upload existing audio file ----

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetUI();

  const file = audioFileInput.files[0];
  if (!file) {
    showError("Please choose an audio file first.");
    return;
  }

  const formData = new FormData();
  formData.append("audio_file", file);

  await processFormData(formData, "Uploading file…", "Transcribing audio…");
});

// ---- Process FormData (shared by upload + live recording) ----

async function processFormData(formData, initialLabel = "Processing…", transcribingLabel = "Transcribing…") {
  try {
    setProgress(5, initialLabel);

    const response = await fetch("/process", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let message = `Server error: ${response.status}`;
      try {
        const data = await response.json();
        if (data && data.error) {
          message = data.error;
        }
      } catch (_) {
        // ignore JSON errors
      }
      setProgress(0, "Error");
      showError(message);
      return;
    }

    setProgress(60, transcribingLabel);

    const data = await response.json();

    setProgress(100, "Done");
    progressSection.style.display = "block";

    if (data.error) {
      showError(data.error);
      return;
    }

    // Update results
    resultsSection.style.display = "block";
    summaryText.textContent = data.summary || "(No summary returned)";
    transcriptText.textContent = data.transcript || "(No transcript)";

    actionItemsList.innerHTML = "";
    if (Array.isArray(data.action_items) && data.action_items.length > 0) {
      data.action_items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        actionItemsList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "(No action items found)";
      actionItemsList.appendChild(li);
    }

    if (data.transcript_file) {
      transcriptFileInfo.textContent = `Transcript saved as: ${data.transcript_file}`;
    } else {
      transcriptFileInfo.textContent = "";
    }

    // ---- NEW: Post-processing buttons (Download PDF + Discard) ----
    if (postActions && downloadPdfBtn && discardBtn && data.download_url && data.discard_url) {
      postActions.style.display = "block";

      // Download PDF
      downloadPdfBtn.href = data.download_url;

      // Discard results
      discardBtn.onclick = async () => {
        const ok = confirm("Discard transcript/summary/action items for this meeting? This cannot be undone.");
        if (!ok) return;

        try {
          const resp = await fetch(data.discard_url, { method: "POST" });
          if (!resp.ok) {
            alert("Discard failed.");
            return;
          }
          resetUI();
          alert("Discarded.");
        } catch (e) {
          console.error(e);
          alert("Discard failed (network error).");
        }
      };
    } else if (postActions) {
      postActions.style.display = "none";
    }



  } catch (err) {
    console.error("Request failed:", err);
    setProgress(0, "Error");
    showError(err.message || "Network or server error.");
  }
}

// ---- "Show transcript folder path" button ----

if (openTranscriptsBtn) {
  openTranscriptsBtn.addEventListener("click", () => {
    // This just shows a message. If you want, you can later add a small
    // endpoint that returns the path or open Finder via a custom scheme.
    alert("Transcripts are saved in the 'transcripts' folder inside your meeting_assistant project.");
  });
}

// ---- Live recording via MediaRecorder ----

let mediaRecorder = null;
let recordedChunks = [];
let recordingStream = null;

function setLiveStatus(message) {
  liveStatus.textContent = message || "";
}

function setLiveButtonsState({ canRecord, canPause, canStop }) {
  recordBtn.disabled = !canRecord;
  pauseBtn.disabled = !canPause;
  stopBtn.disabled = !canStop;
}

// Start a new recording
recordBtn.addEventListener("click", async () => {
  resetUI();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showError("Live recording is not supported in this browser.");
    return;
  }

  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    recordedChunks = [];
    mediaRecorder = new MediaRecorder(recordingStream);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    };

    mediaRecorder.onstart = () => {
      setLiveStatus("Recording…");
      setLiveButtonsState({ canRecord: false, canPause: true, canStop: true });
    };

    mediaRecorder.onpause = () => {
      setLiveStatus("Recording paused.");
    };

    mediaRecorder.onresume = () => {
      setLiveStatus("Recording…");
    };

    mediaRecorder.onstop = async () => {
      setLiveStatus("Processing recording…");
      setLiveButtonsState({ canRecord: true, canPause: false, canStop: false });

      if (recordingStream) {
        recordingStream.getTracks().forEach((track) => track.stop());
        recordingStream = null;
      }

      if (!recordedChunks.length) {
        showError("No audio was recorded.");
        setLiveStatus("");
        return;
      }

      const blob = new Blob(recordedChunks, { type: "audio/webm" });
      const file = new File([blob], "live_recording.webm", { type: "audio/webm" });

      const formData = new FormData();
      formData.append("audio_file", file);

      await processFormData(formData, "Uploading recording…", "Transcribing recording…");
      setLiveStatus("Recording processed.");
    };

    mediaRecorder.start();
  } catch (err) {
    console.error("Error starting recording:", err);
    showError("Could not access microphone. Check browser permissions.");
    setLiveButtonsState({ canRecord: true, canPause: false, canStop: false });
  }
});

// Pause / resume
pauseBtn.addEventListener("click", () => {
  if (!mediaRecorder) return;

  if (mediaRecorder.state === "recording") {
    mediaRecorder.pause();
    pauseBtn.textContent = "▶ Resume";
  } else if (mediaRecorder.state === "paused") {
    mediaRecorder.resume();
    pauseBtn.textContent = "⏸ Pause";
  }
});

// Stop and send
stopBtn.addEventListener("click", () => {
  if (!mediaRecorder) return;

  if (mediaRecorder.state === "recording" || mediaRecorder.state === "paused") {
    mediaRecorder.stop();
    pauseBtn.textContent = "⏸ Pause";
  }
});

// Initial state for live buttons
setLiveButtonsState({ canRecord: true, canPause: false, canStop: false });
setLiveStatus("");
