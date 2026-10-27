(() => {
  const form = document.getElementById('brief-form');
  if (!form) return;

  const messageInput = document.getElementById('client-message');
  const characterCount = document.getElementById('character-count');
  const analyzeButton = document.getElementById('analyze-button');
  const formError = document.getElementById('form-error');
  const reportEmpty = document.getElementById('report-empty');
  const reportContent = document.getElementById('report-content');
  const reportActions = document.getElementById('report-actions');
  const warningBox = document.getElementById('mode-warning');
  const sampleButton = document.getElementById('load-example');
  const sampleBrief = "Hi! We run a small bakery and need a website before our new branch opens. We'd like customers to see our menu and cake designs, read our story, and send custom cake enquiries through a form. The website should look modern and warm, work well on phones, and be easy for our team to update. We already have a logo and some photos, but need help organizing the content. We may want online payments later, but for the first version we're mainly looking for enquiries and a clear menu. We need to review the first design before the full site is built.";
  let currentAnalysis = null;
  let currentBriefId = null;

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);

  const textOrFallback = (value, fallback = 'Not specified yet.') => {
    const text = String(value ?? '').trim();
    return text || fallback;
  };

  const renderList = (elementId, values, className = '') => {
    const element = document.getElementById(elementId);
    if (!element) return;
    const items = Array.isArray(values) ? values : [];
    element.className = className || element.className;
    element.innerHTML = items.length
      ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
      : '<li>No items were identified.</li>';
  };

  const renderRisks = (risks) => {
    const element = document.getElementById('risks-list');
    const items = Array.isArray(risks) ? risks : [];
    element.innerHTML = items.length ? items.map((risk) => {
      const level = ['Low', 'Medium', 'High'].includes(risk.level) ? risk.level : 'Medium';
      const lowerLevel = level.toLowerCase();
      return `<article class="risk-item"><span class="risk-level ${lowerLevel}">${escapeHtml(level)}</span><div><h4>${escapeHtml(risk.title)}</h4><p>${escapeHtml(risk.detail)}</p></div></article>`;
    }).join('') : '<p class="result-summary">No specific risks were identified. Review the scope boundaries before quoting.</p>';
  };

  const setTab = (tabName) => {
    document.querySelectorAll('.result-tab').forEach((button) => {
      const active = button.dataset.tab === tabName;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    document.querySelectorAll('.result-panel').forEach((panel) => {
      panel.hidden = panel.dataset.panel !== tabName;
    });
  };

  const renderResults = (data, briefId, mode, exportUrl, warning = '') => {
    currentAnalysis = data;
    currentBriefId = briefId;
    reportEmpty.hidden = true;
    reportContent.hidden = false;
    reportActions.hidden = false;
    warningBox.hidden = !warning;
    warningBox.textContent = warning ? `Gemini could not be used, so a local rules-based brief was created instead. Details: ${warning}` : '';

    document.getElementById('analysis-mode').textContent = String(mode || 'LOCAL RULES').toUpperCase();
    document.getElementById('brief-number').textContent = `BRIEF #${String(briefId ?? '').padStart(4, '0')}`;
    document.getElementById('result-title').textContent = textOrFallback(data.title, 'Client project brief');
    document.getElementById('result-summary').textContent = textOrFallback(data.summary);
    document.getElementById('question-count').textContent = Array.isArray(data.questions) ? data.questions.length : 0;
    document.getElementById('goal-count').textContent = `${(data.goals || []).length} captured`;
    document.getElementById('requirement-count').textContent = `${(data.requirements || []).length} captured`;
    document.getElementById('risk-count').textContent = `${(data.risks || []).length} to review`;

    renderList('goals-list', data.goals, 'plain-list');
    renderList('requirements-list', data.requirements, 'numbered-list');
    renderList('deliverables-list', data.deliverables, 'check-list');
    renderList('questions-list', data.questions, 'question-list');
    renderList('boundaries-list', data.boundaries, 'boundary-list');
    renderList('acceptance-list', data.acceptance_criteria, 'check-list');
    renderRisks(data.risks);
    document.getElementById('client-summary').textContent = textOrFallback(data.client_summary);
    document.getElementById('suggested-next-step').textContent = textOrFallback(data.suggested_next_step);
    document.getElementById('export-link').href = exportUrl || '#';
    setTab('overview');
  };

  const showError = (message) => {
    formError.textContent = message;
    formError.hidden = false;
  };

  const clearError = () => {
    formError.hidden = true;
    formError.textContent = '';
  };

  const copyText = async (text, button) => {
    const original = button.textContent;
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = 'Copied';
    } catch (error) {
      const temp = document.createElement('textarea');
      temp.value = text;
      temp.style.position = 'fixed';
      temp.style.opacity = '0';
      document.body.appendChild(temp);
      temp.select();
      const succeeded = document.execCommand('copy');
      temp.remove();
      button.textContent = succeeded ? 'Copied' : 'Select and copy manually';
    }
    window.setTimeout(() => { button.textContent = original; }, 1800);
  };

  const updateCharacterCount = () => {
    characterCount.textContent = `${messageInput.value.length.toLocaleString()} characters`;
  };

  messageInput.addEventListener('input', updateCharacterCount);
  updateCharacterCount();

  sampleButton.addEventListener('click', () => {
    messageInput.value = sampleBrief;
    document.getElementById('project-type').value = 'Website';
    updateCharacterCount();
    clearError();
    messageInput.focus();
  });

  document.querySelectorAll('.result-tab').forEach((button) => {
    button.addEventListener('click', () => setTab(button.dataset.tab));
  });

  document.getElementById('copy-summary').addEventListener('click', (event) => {
    if (currentAnalysis) copyText(currentAnalysis.client_summary || '', event.currentTarget);
  });
  document.getElementById('copy-client-summary').addEventListener('click', (event) => {
    if (currentAnalysis) copyText(currentAnalysis.client_summary || '', event.currentTarget);
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearError();
    warningBox.hidden = true;
    const clientMessage = messageInput.value.trim();
    if (clientMessage.length < 20) {
      showError('Add a little more detail. The client message must contain at least 20 characters.');
      messageInput.focus();
      return;
    }
    if (clientMessage.length > 20000) {
      showError('The client message must be under 20,000 characters.');
      return;
    }

    const originalButtonText = analyzeButton.querySelector('span').textContent;
    analyzeButton.disabled = true;
    analyzeButton.querySelector('span').textContent = 'Structuring the brief...';
    analyzeButton.querySelector('.button-arrow').textContent = '…';

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_message: clientMessage,
          project_type: document.getElementById('project-type').value,
          budget: document.getElementById('budget').value.trim(),
          deadline: document.getElementById('deadline').value.trim()
        })
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Could not create the brief. Please try again.');
      renderResults(result.analysis, result.id, result.mode, result.export_url, result.warning);
      if (result.saved_url) history.replaceState({}, '', result.saved_url);
      reportContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      showError(error.message || 'Something went wrong. Check that the Flask server is running and try again.');
    } finally {
      analyzeButton.disabled = false;
      analyzeButton.querySelector('span').textContent = originalButtonText;
      analyzeButton.querySelector('.button-arrow').textContent = '↗';
    }
  });

  if (window.SCOPECNOTE_INITIAL_DATA) {
    const initialMode = window.SCOPECNOTE_INITIAL_MODE || 'Saved brief';
    renderResults(window.SCOPECNOTE_INITIAL_DATA, window.SCOPECNOTE_INITIAL_ID, initialMode, window.SCOPECNOTE_INITIAL_EXPORT);
  }
})();
