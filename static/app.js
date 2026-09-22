/* Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 */
(() => {
  const files = document.getElementById('statement-files');
  const queue = document.getElementById('file-queue');
  const form = document.getElementById('upload-form');
  const status = document.getElementById('system-status');
  const effects = document.getElementById('effects-toggle');

  const bytes = (size) => size > 1048576 ? `${(size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(size / 1024))} KB`;

  files?.addEventListener('change', () => {
    const selected = Array.from(files.files);
    if (!selected.length) {
      queue.innerHTML = '<p class="empty-queue">FILES QUEUED: 00 // SYSTEM READY</p>';
      return;
    }
    queue.innerHTML = `<div class="queue-header">FILES QUEUED: ${String(selected.length).padStart(2, '0')}</div>` + selected.map((file, index) => `
      <div class="queued-file">
        <div><span class="file-index">${String(index + 1).padStart(2, '0')}</span><strong>${file.name.replace(/[&<>"']/g, '')}</strong><small>${bytes(file.size)} // AWAITING SCAN</small></div>
        <label><span>FILE PASSWORD</span><input type="password" name="password_${index}" autocomplete="off" placeholder="ONLY IF REQUIRED"></label>
      </div>`).join('');
    status.textContent = 'SYSTEM STATUS: FILES READY';
  });

  form?.addEventListener('submit', () => {
    status.textContent = 'SYSTEM STATUS: SCANNING // RECONCILING // IMPORTING';
    document.getElementById('import-button').disabled = true;
    document.getElementById('import-button').textContent = '> PROCESSING...';
  });

  document.querySelectorAll('[data-setup-form]').forEach((setupForm) => {
    setupForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const panel = document.getElementById('setup-progress');
      const error = document.getElementById('setup-error');
      const buttons = document.querySelectorAll('[data-setup-form] button[type="submit"]');
      const started = Date.now();
      panel.hidden = false;
      panel.querySelector('progress').hidden = false;
      panel.setAttribute('aria-busy', 'true');
      error.hidden = true;
      buttons.forEach(button => { button.disabled = true; });
      const timer = setInterval(() => {
        const seconds = Math.floor((Date.now() - started) / 1000);
        document.getElementById('setup-elapsed').textContent = `Elapsed: ${seconds} seconds`;
        if (seconds > 120) document.getElementById('setup-help').textContent = 'This is taking longer than usual. The step above is still running. Keep this window open; do not start another setup.';
      }, 1000);
      let polling = true;
      const poll = async () => {
        try {
          const response = await fetch('/setup/progress', {signal: AbortSignal.timeout(5000)});
          if (response.ok) {
            const status = await response.json();
            document.getElementById('setup-stage').textContent = status.message;
          }
        } catch { /* The setup POST remains authoritative if a status poll fails. */ }
        if (polling) setTimeout(poll, 1000);
      };
      poll();
      try {
        const response = await fetch('/setup', {method: 'POST', body: new FormData(setupForm), headers: {'X-Setup-Request': '1'}});
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Setup could not finish. Review your settings and retry.');
        window.location.assign(result.next);
      } catch (failure) {
        error.textContent = `${failure.message} Your settings remain available below. If the connection to the app was lost, reload to check whether setup is still running before retrying.`;
        error.hidden = false;
        buttons.forEach(button => { button.disabled = false; });
      } finally {
        polling = false;
        clearInterval(timer);
        panel.setAttribute('aria-busy', 'false');
        panel.querySelector('progress').hidden = true;
      }
    });
  });

  const storedEffects = localStorage.getItem('retro-effects') !== 'off';
  document.documentElement.dataset.effects = storedEffects ? 'on' : 'off';
  if (effects) effects.textContent = storedEffects ? '[ FX: ON ]' : '[ FX: OFF ]';
  effects?.addEventListener('click', () => {
    const enabled = document.documentElement.dataset.effects !== 'on';
    document.documentElement.dataset.effects = enabled ? 'on' : 'off';
    localStorage.setItem('retro-effects', enabled ? 'on' : 'off');
    effects.textContent = enabled ? '[ FX: ON ]' : '[ FX: OFF ]';
  });
})();
