// api.js — handles sending image to backend and managing stage progress
// Expects: <body data-api="/scan"> to configure endpoint
// Hooks into UI in ui.js via window.UI functions.

(() => {
  const body = document.body;
  const apiUrl = body.getAttribute('data-api') || '/scan';

  const scanBtn = document.getElementById('scanBtn');
  const resultsPlaceholder = document.getElementById('resultsPlaceholder');
  const resultPanel = document.getElementById('resultPanel');

  async function runScan() {
    // get image file from Camera module
    const file = await window.Camera.getFile();
    if (!file) {
      alert('No image. Upload or capture an image before scanning.');
      return;
    }

    // Prepare UI
    resultsPlaceholder.style.display = 'none';
    resultPanel.style.display = 'none';
    window.UI && window.UI.startScan(); // animate scanline & stages

    // Build form
    const form = new FormData();
    form.append('image', file);

    // Optional: add metadata if needed
    // form.append('type', 'cognitive');

    // Start fetch and fake staged progress while waiting (backend may be quick)
    try {
      // Kick off progress simulation
      window.UI && window.UI.setStageProgress(1, 30);
      const resp = await fetch(apiUrl, {
        method: 'POST',
        body: form
      });

      // Backend may take time — update staged progress
      window.UI && window.UI.setStageProgress(1, 60);
      window.UI && window.UI.setStageProgress(2, 20);

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `Scan failed (${resp.status})`);
      }

      const data = await resp.json();

      // Finalize progress
      window.UI && window.UI.setStageProgress(2, 100);
      window.UI && window.UI.setStageProgress(3, 40);

      // render results
      renderResults(data);

      window.UI && window.UI.setStageProgress(3, 100);
      window.UI && window.UI.finishScan(null, data);
    } catch (err) {
      console.error('scan error', err);
      window.UI && window.UI.finishScan(err);
      resultsPlaceholder.style.display = 'block';
      resultsPlaceholder.textContent = 'Scan failed: ' + (err.message || 'unknown');
    }
  }

  function renderResults(data) {
    const summaryEl = document.getElementById('healthSummary');
    const highlightsList = document.getElementById('highlightsList');
    const recommendationsList = document.getElementById('recommendationsList');
    const confidenceBadge = document.getElementById('confidenceBadge');
    const regionsNote = document.getElementById('regionsNote');

    // Safety checks
    data = data || {};
    const healthScore = (typeof data.healthScore === 'number') ? data.healthScore : (data.score || 0);
    const confidence = Math.round((data.confidence ?? 0) * 100) || (data.healthScore ? 90 : 0);

    // Set summary
    summaryEl.textContent = data.summary || data.message || 'No summary provided';

    // Fill lists
    highlightsList.innerHTML = '';
    (data.highlights || []).forEach(h => {
      const li = document.createElement('li'); li.textContent = h; highlightsList.appendChild(li);
    });

    recommendationsList.innerHTML = '';
    (data.recommendations || []).forEach(r => {
      const li = document.createElement('li'); li.textContent = r; recommendationsList.appendChild(li);
    });

    confidenceBadge.textContent = 'Confidence: ' + (data.confidence ? Math.round(data.confidence * 100) + '%' : confidence + '%');

    // Regions
    if (Array.isArray(data.regions) && data.regions.length) {
      regionsNote.textContent = `${data.regions.length} region(s) detected — highlights drawn on preview.`;
      // ask UI to draw overlays if available
      window.UI && window.UI.drawRegions(data.regions);
    } else {
      regionsNote.textContent = '';
    }

    // animate circular score
    window.UI && window.UI.animateScore(healthScore);

    // show results
    resultPanel.style.display = 'block';
  }

  scanBtn && scanBtn.addEventListener('click', runScan);

})();
