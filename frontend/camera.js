// camera.js — camera + capture logic
// Attaches to IDs used in the HTML pages: videoPreview, imgPreview, fileInput, openCam, capture, clearBtn

(() => {
  const video = document.getElementById('videoPreview');
  const img = document.getElementById('imgPreview');
  const fileInput = document.getElementById('fileInput');
  const openCamBtn = document.getElementById('openCam');
  const captureBtn = document.getElementById('capture');
  const clearBtn = document.getElementById('clearBtn');

  let stream = null;
  let lastFile = null;

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Camera not available. Use file upload instead.');
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
      video.srcObject = stream;
      video.play();
      video.style.display = 'block';
      img.style.display = 'none';
      // show HUD scanline via ui
      window.UI && window.UI.startCameraHUD();
    } catch (err) {
      console.error('camera error', err);
      alert('Unable to access camera. Check permissions.');
    }
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    video.pause();
    video.srcObject = null;
    window.UI && window.UI.stopCameraHUD();
  }

  async function captureImage() {
    const activeVideo = video && video.srcObject;
    const w = activeVideo ? (video.videoWidth || 1280) : 1280;
    const h = activeVideo ? (video.videoHeight || 720) : 720;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (activeVideo) {
      ctx.drawImage(video, 0, 0, w, h);
    } else {
      alert('Start the camera to capture an image, or upload a file.');
      return;
    }
    return new Promise(resolve => {
      canvas.toBlob(blob => {
        const file = new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' });
        lastFile = file;
        previewFile(file);
        resolve(file);
      }, 'image/jpeg', 0.9);
    });
  }

  function previewFile(file) {
    const url = URL.createObjectURL(file);
    img.src = url;
    img.style.display = 'block';
    video.style.display = 'none';
  }

  function clearPreview() {
    lastFile = null;
    img.src = '';
    img.style.display = 'none';
    video.style.display = 'none';
    stopCamera();
    window.UI && window.UI.resetHUD();
  }

  fileInput && fileInput.addEventListener('change', (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) {
      lastFile = f;
      previewFile(f);
      window.UI && window.UI.previewReady();
    }
  });

  openCamBtn && openCamBtn.addEventListener('click', async () => {
    if (stream) { stopCamera(); openCamBtn.textContent = 'Open Camera'; return; }
    await startCamera();
    openCamBtn.textContent = 'Close Camera';
  });

  captureBtn && captureBtn.addEventListener('click', async () => {
    if (!stream) {
      alert('Open the camera first or upload a file.');
      return;
    }
    const file = await captureImage();
    window.UI && window.UI.previewReady();
  });

  clearBtn && clearBtn.addEventListener('click', () => {
    clearPreview();
    if (fileInput) fileInput.value = '';
  });

  // Expose helper to fetch the last file for API upload
  window.Camera = {
    async getFile() {
      // if video is active and we haven't captured, capture a fresh frame
      if (stream && !lastFile) {
        lastFile = await captureImage();
      }
      return lastFile;
    },
    stopCamera
  };
})();
