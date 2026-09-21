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
