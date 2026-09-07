'use strict';
(() => {
  const root = document.documentElement;
  const themeButtons = document.querySelectorAll('.theme-toggle');
  function applyTheme(theme) {
    root.dataset.theme = theme;
    themeButtons.forEach(button => {
      button.setAttribute('aria-label', theme === 'dark' ? 'Activer le thème clair' : 'Activer le thème sombre');
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      const icon = button.querySelector('.theme-icon');
      if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌑';
    });
  }
  let savedTheme;
  try { savedTheme = localStorage.getItem('theme'); } catch (_) { /* Private mode can disable storage. */ }
  applyTheme(savedTheme === 'dark' ? 'dark' : 'light');
  themeButtons.forEach(button => button.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try { localStorage.setItem('theme', next); } catch (_) { /* Theme still works without persistence. */ }
  }));

  const menuButton = document.getElementById('menu-toggle');
  const navigation = document.getElementById('navigation');
  function closeMenu() {
    if (!menuButton) return;
    navigation.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Ouvrir le menu');
  }
  if (menuButton) {
    menuButton.addEventListener('click', () => {
      const open = navigation.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
    });
    navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && navigation.classList.contains('open')) { closeMenu(); menuButton.focus(); } });
    document.addEventListener('click', e => { if (!navigation.contains(e.target) && !menuButton.contains(e.target)) closeMenu(); });
    matchMedia('(min-width: 651px)').addEventListener('change', closeMenu);
  }

  const form = document.getElementById('ent-form');
  if (!form) return;
  const config = Object.assign({ apiUrl: '/api/generate', maxFileBytes: 5242880, timeoutMs: 120000 }, window.ENT_CONFIG);
  const fileInput = document.getElementById('cv-file');
  const dropzone = document.getElementById('dropzone');
  const entreprise = document.getElementById('entreprise');
  const offer = document.getElementById('offre');
  const status = document.getElementById('ent-status');
  const submit = document.getElementById('ent-submit-btn');
  const downloadWrap = document.getElementById('ent-download-wrap');
  const downloadLink = document.getElementById('ent-download-link');
  const cancel = document.getElementById('cancel-generation');
  let objectUrl = null;
  let controller = null;

  function message(text, type = '') { status.hidden = false; status.className = type; status.textContent = text; }
  function clearResult() {
    if (objectUrl) { URL.revokeObjectURL(objectUrl); objectUrl = null; }
    downloadWrap.hidden = true;
    downloadLink.removeAttribute('href');
  }
  function validFile(file) {
    if (!file) return 'Sélectionnez le CV utilisé pour postuler.';
    if (!/\.(pdf|docx)$/i.test(file.name)) return 'Ce format n\u2019est pas accepté. Choisissez un fichier PDF ou DOCX.';
    if (file.size === 0) return 'Ce fichier est vide. Sélectionnez un autre document.';
    if (file.size > config.maxFileBytes) return 'Votre fichier dépasse 5 Mo. Réduisez sa taille ou choisissez un autre document.';
    return '';
  }
  function updateFile() {
    clearResult();
    const file = fileInput.files[0];
    const error = file ? validFile(file) : '';
    fileInput.setCustomValidity(error);
    const fileLabel = document.getElementById('file-label');
    const fileStatus = document.getElementById('file-status');
    if (fileLabel) fileLabel.textContent = file ? file.name : 'Glissez votre CV ici';
    if (fileStatus) fileStatus.textContent = file ? (file.size / 1024 / 1024).toLocaleString('fr-FR', { maximumFractionDigits: 2 }) + ' Mo · Cliquez pour remplacer' : 'ou parcourez vos fichiers';
    const fileActions = document.getElementById('file-actions');
    if (fileActions) fileActions.hidden = !file;
    if (error) message(error, 'error'); else status.hidden = true;
  }
  if (fileInput) fileInput.addEventListener('change', updateFile);
  const removeFileBtn = document.getElementById('remove-file');
  if (removeFileBtn) removeFileBtn.addEventListener('click', () => { fileInput.value = ''; updateFile(); fileInput.focus(); });

  if (dropzone) {
    ['dragenter', 'dragover'].forEach(event => dropzone.addEventListener(event, e => { e.preventDefault(); if (!controller) dropzone.classList.add('dragover'); }));
    ['dragleave', 'drop'].forEach(event => dropzone.addEventListener(event, () => dropzone.classList.remove('dragover')));
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      if (controller) return;
      const files = e.dataTransfer.files;
      if (files.length !== 1) { message('Déposez un seul CV à la fois.', 'error'); return; }
      try { fileInput.files = files; updateFile(); } catch (_) { message('Utilisez le bouton de sélection pour ajouter votre fichier.', 'error'); }
    });
  }

  const offerCount = document.getElementById('offer-count');
  if (offer && offerCount) {
    offer.addEventListener('input', () => {
      offerCount.textContent = offer.value.length.toLocaleString('fr-FR') + ' / 30 000';
      offer.setCustomValidity('');
      clearResult();
    });
  }

  function setBusy(busy) {
    form.querySelectorAll('input, textarea, button').forEach(control => { control.disabled = busy; });
    const label = submit.querySelector('span');
    if (label) label.textContent = busy ? 'Votre préparation prend forme…' : 'Générer ma préparation';
    form.setAttribute('aria-busy', String(busy));
    if (cancel) { cancel.hidden = !busy; cancel.disabled = false; }
  }
  if (cancel) cancel.addEventListener('click', () => controller?.abort());

  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (controller) return;
    clearResult();
    const file = fileInput.files[0];
    const error = validFile(file);
    if (error) { message(error, 'error'); fileInput.focus(); return; }
    if (!entreprise.value.trim()) { entreprise.setCustomValidity('Indiquez le nom de l\u2019entreprise.'); entreprise.reportValidity(); return; }
    entreprise.setCustomValidity('');
    if (!offer.value.trim()) { offer.setCustomValidity('Collez le texte de la fiche de poste.'); offer.reportValidity(); return; }
    offer.setCustomValidity('');
    if (!form.reportValidity()) return;

    const data = new FormData();
    data.append('cv', file);
    data.append('entreprise', entreprise.value.trim());
    data.append('offre', offer.value.trim());
    const format = form.elements.format.value;
    data.append('format', format);

    controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller?.abort(); }, config.timeoutMs);
    setBusy(true);
    message('Préparation en cours. Le traitement prend généralement 30 à 40 secondes. Vous pouvez patienter sur cette page.');
    try {
      const response = await fetch(config.apiUrl, { method: 'POST', body: data, signal: controller.signal, credentials: 'same-origin' });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const detail = typeof payload.detail === 'string' ? payload.detail : '';
        if (response.status === 429) throw new Error('Le service reçoit beaucoup de demandes. Patientez quelques instants avant de réessayer.');
        if (response.status === 413) throw new Error('Le serveur refuse ce fichier car il est trop volumineux. Essayez un document plus léger.');
        throw new Error(detail || 'La génération est momentanément indisponible. Réessayez dans quelques instants.');
      }
      const blob = await response.blob();
      objectUrl = URL.createObjectURL(blob);
      const disposition = response.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const filename = match ? match[1].replace(/[\\/\x00-\x1f]/g, '_') : ('Preparation_Entretien.' + format);
      downloadLink.href = objectUrl;
      downloadLink.download = filename;
      downloadWrap.hidden = false;
      message('Votre préparation est prête. Téléchargez-la, puis relisez-la avant votre entretien.', 'ok');
      downloadLink.focus();
    } catch (error) {
      if (error.name === 'AbortError') message(timedOut ? 'Le traitement prend plus de temps que prévu. Vos champs sont conservés. Vous pouvez réessayer plus tard.' : 'L\u2019attente a été arrêtée. Le traitement peut se poursuivre côté serveur. Vos champs sont conservés.', 'error');
      else if (error instanceof TypeError) message('Impossible de joindre le service. Vérifiez votre connexion et réessayez. Si le problème persiste, le service est peut-être indisponible.', 'error');
      else message(error.message || 'Une erreur est survenue. Réessayez dans quelques instants.', 'error');
    } finally {
      clearTimeout(timer);
      controller = null;
      setBusy(false);
    }
  });

  window.addEventListener('pagehide', () => { if (objectUrl) URL.revokeObjectURL(objectUrl); controller?.abort(); });
})();
