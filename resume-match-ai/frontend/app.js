const API = window.TALENTSCOPE_API_URL || window.location.origin;
const state = {
  title: 'Backend Software Engineer',
  jdText: '',
  jdFile: null,
  resumes: [],
  dragging: false,
  job: null,
  results: [],
  selected: null,
  detail: null,
  search: '',
  sort: 'score',
  busy: false,
  detailBusy: false,
  error: '',
  notice: '',
  engine: '',
  rejected: [],
};

const iconPaths = {
  sparkles: '<path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 14 1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14Z"/>',
  briefcase: '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
  upload: '<path d="M12 16V4m-5 5 5-5 5 5"/><path d="M20 16.5v2A2.5 2.5 0 0 1 17.5 21h-11A2.5 2.5 0 0 1 4 18.5v-2"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5"/><path d="M5 17v3h14v-3"/>',
  shield: '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3m.1 4h.01"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.6 9a7 7 0 0 1 11.6-2L20 12M4 12l2.8 5a7 7 0 0 0 11.6-2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  close: '<path d="m18 6-12 12M6 6l12 12"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  checkCircle: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  arrow: '<path d="M7 17 17 7M7 7h10v10"/>',
  loader: '<path d="M21 12a9 9 0 1 1-6.2-8.6"/>',
};

function icon(name, className = '', size = 16) {
  return `<svg class="${className}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || ''}</svg>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

function scoreClass(score) {
  if (score >= 80) return 'excellent';
  if (score >= 65) return 'good';
  return 'low';
}

function isSupportedDocument(file) {
  const filename = String(file.name || '').trim();
  const mimeType = String(file.type || '').toLowerCase().split(';')[0];
  return /\.(pdf|docx)$/i.test(filename) ||
    mimeType === 'application/pdf' ||
    mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
}

function scorePill(score) {
  return `<span class="score-pill ${scoreClass(Number(score) || 0)}">${(Number(score) || 0).toFixed(1)}%</span>`;
}

function skillPills(skills, kind = 'matched') {
  if (!skills?.length) return '<span class="muted">None identified</span>';
  return `<div class="pills">${skills.map(skill => `<span class="skill-pill ${kind}">${escapeHtml(skill)}</span>`).join('')}</div>`;
}

function initials(name) {
  return String(name || '?').split(' ').map(part => part[0]).slice(0, 2).join('').toUpperCase();
}

function filteredResults() {
  let items = [...state.results];
  if (state.search.trim()) {
    const term = state.search.toLowerCase();
    items = items.filter(row =>
      (row.name || '').toLowerCase().includes(term) ||
      (row.email || '').toLowerCase().includes(term) ||
      (row.matched_skills || []).some(skill => skill.toLowerCase().includes(term))
    );
  }
  if (state.sort === 'name') items.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  else if (state.sort === 'experience') items.sort((a, b) => (b.experience_years || 0) - (a.experience_years || 0));
  else items.sort((a, b) => b.match_score - a.match_score);
  return items;
}

function renderRequirements() {
  const requirements = state.job?.requirements;
  if (!requirements) return '';
  return `<div class="detected-requirements"><strong>Required</strong>${skillPills(requirements.skills)}<strong>Preferred</strong>${skillPills(requirements.preferred_skills)}${requirements.required_experience_years ? `<span class="req-text">${escapeHtml(requirements.required_experience_years)}+ years requested</span>` : ''}</div>`;
}

function renderRows() {
  const items = filteredResults();
  const rows = items.map((candidate, index) => `
    <tr data-candidate-id="${Number(candidate.id)}" class="${state.selected === candidate.id ? 'selected-row' : ''}">
      <td class="rank-col"><span class="rank-number ${index === 0 && state.sort === 'score' ? 'rank-first' : ''}">${String(index + 1).padStart(2, '0')}</span></td>
      <td><div class="candidate-cell"><div class="candidate-avatar">${escapeHtml(initials(candidate.name))}</div><div><strong>${escapeHtml(candidate.name)}</strong><span>${escapeHtml(candidate.email || candidate.file_name)}</span></div></div></td>
      <td><span class="experience-text">${candidate.experience_years == null ? 'Not detected' : `${escapeHtml(candidate.experience_years)} yrs`}</span></td>
      <td>${scorePill(candidate.match_score)}</td>
      <td><div class="table-skills">${(candidate.matched_skills || []).slice(0, 3).map(skill => `<span>${escapeHtml(skill)}</span>`).join('')}${(candidate.matched_skills || []).length > 3 ? `<span class="more-skills">+${candidate.matched_skills.length - 3}</span>` : ''}${!candidate.matched_skills?.length ? '<span class="muted">—</span>' : ''}</div></td>
      <td><button class="row-open" aria-label="Open ${escapeHtml(candidate.name)}">${icon('arrow')}</button></td>
    </tr>`).join('');
  return { items, rows: rows || `<tr><td colspan="6" class="empty-state">${state.results.length ? 'No candidates match this search.' : 'No resumes were successfully analyzed.'}</td></tr>` };
}

function renderDetail() {
  const detail = state.detail;
  if (!detail) return '';
  const analysis = detail.analysis || {};
  const extracted = detail.extracted || {};
  const components = analysis.score_components || {};
  const rows = [
    ['Skills coverage', components.skills, '50% base weight'],
    ['Content similarity', components.semantic_similarity, '25% base weight'],
    ['Experience fit', components.experience, '15% base weight'],
    ['Education fit', components.education, '10% base weight'],
  ].filter(row => row[1] !== null && row[1] !== undefined);
  return `<div class="detail-grid">
    <div class="detail-main">
      <div class="candidate-profile-card">
        <div class="profile-avatar">${escapeHtml(initials(detail.name))}</div>
        <div class="profile-main"><h3>${escapeHtml(detail.name)}</h3><p>${escapeHtml(detail.email || 'Email not detected')}${detail.phone ? ` · ${escapeHtml(detail.phone)}` : ''}</p><div class="profile-tags"><span>${detail.experience_years == null ? 'Experience not detected' : `${escapeHtml(detail.experience_years)} years experience`}</span><span>${escapeHtml(extracted.education?.level || 'Education not detected')}</span></div></div>
        <div class="profile-score">${scorePill(detail.match_score)}<span>OVERALL MATCH</span></div>
      </div>
      <div class="detail-card"><div class="detail-card-title"><h3>Skill comparison</h3><span>${analysis.matched_skills?.length || 0} of ${(analysis.matched_skills?.length || 0) + (analysis.missing_skills?.length || 0)} identified skills</span></div><div class="skill-group"><label>${icon('checkCircle')} MATCHED SKILLS</label>${skillPills(analysis.matched_skills)}</div><div class="skill-group missing-group"><label>${icon('close')} MISSING REQUIRED SKILLS</label>${skillPills(analysis.missing_skills, 'missing')}</div>${(analysis.matched_preferred_skills?.length || analysis.missing_preferred_skills?.length) ? `<div class="skill-group missing-group"><label>${icon('sparkles')} PREFERRED SKILLS</label>${skillPills(analysis.matched_preferred_skills)}<div style="height:6px"></div>${skillPills(analysis.missing_preferred_skills, 'missing')}</div>` : ''}</div>
      <div class="detail-card"><div class="detail-card-title"><h3>Why this score?</h3><span>Weighted scoring breakdown</span></div><div class="score-breakdown">${rows.map(([label, value, weight]) => `<div class="breakdown-row"><div class="breakdown-meta"><strong>${label}</strong><span>${Number(value).toFixed(1)} / 100 <i>${weight}</i></span></div><div class="progress-track"><div class="progress-fill ${scoreClass(value)}" style="width:${Math.max(0, Math.min(100, Number(value)))}%"></div></div></div>`).join('')}</div><div class="reason-list">${(analysis.reasons || []).map(reason => `<div>${icon('check')}${escapeHtml(reason)}</div>`).join('')}</div></div>
    </div>
    <aside class="detail-side">
      <div class="detail-card extracted-card"><div class="detail-card-title"><h3>Extracted profile</h3>${icon('file')}</div><dl><dt>Candidate</dt><dd>${escapeHtml(detail.name)}</dd><dt>Email</dt><dd>${escapeHtml(detail.email || 'Not found')}</dd><dt>Phone</dt><dd>${escapeHtml(detail.phone || 'Not found')}</dd><dt>Experience</dt><dd>${detail.experience_years == null ? 'Not detected' : `${escapeHtml(detail.experience_years)} years`}</dd><dt>Education</dt><dd>${escapeHtml(extracted.education?.level || 'Not detected')}</dd><dt>Source file</dt><dd class="source-file">${escapeHtml(detail.file_name)}</dd></dl></div>
      <div class="detail-card"><div class="detail-card-title"><h3>Resume text preview</h3></div><p class="resume-preview">${escapeHtml(detail.resume_preview || 'No preview available.')}</p></div>
    </aside>
  </div>`;
}

function render() {
  const active = document.activeElement;
  const focusId = active?.dataset?.focus;
  const selectionStart = active && typeof active.selectionStart === 'number' ? active.selectionStart : null;
  const selectionEnd = active && typeof active.selectionEnd === 'number' ? active.selectionEnd : null;
  const visible = filteredResults();
  const average = state.results.length ? state.results.reduce((sum, item) => sum + item.match_score, 0) / state.results.length : 0;
  const topScore = state.results.length ? Math.max(...state.results.map(item => item.match_score)) : 0;
  const avgSkills = state.results.length ? Math.round(state.results.reduce((sum, item) => sum + (item.matched_skills?.length || 0), 0) / state.results.length) : 0;
  const table = renderRows();
  const missingRequirements = [];
  if (state.jdText.trim().length < 10 && !state.jdFile) {
    missingRequirements.push('add a job description with at least 10 characters or upload a PDF/DOCX');
  }
  if (!state.resumes.length) missingRequirements.push('select at least one PDF/DOCX resume');

  document.getElementById('app').innerHTML = `
    <div class="app-shell">
      <header class="topbar"><div class="brand-lockup"><div class="brand-mark">${icon('sparkles', '', 19)}</div><div><div class="brand-name">talent<span>scope</span></div><div class="brand-caption">AI-ASSISTED RECRUITING WORKSPACE</div></div></div><div class="topbar-right"><span class="status-dot"></span> Prototype environment <span class="topbar-divider"></span><span class="avatar">R</span> Recruiter</div></header>
      <main class="page-wrap">
        <div class="page-heading"><div><div class="eyebrow">CANDIDATE INTELLIGENCE <span> / </span> RESUME SCREENING</div><h1>Resume matching</h1><p class="subheading">Compare candidate profiles against a role, understand the fit, and prioritize review.</p></div>${state.job ? `<button class="button button-secondary" data-action="reset">${icon('refresh')} New analysis</button>` : ''}</div>
        <section class="workflow-grid">
          <div class="panel input-panel">
            <div class="panel-heading"><div class="step-number">01</div><div><h2>Job description</h2><p>Define the role and its requirements.</p></div>${icon('briefcase', 'panel-icon')}</div>
            <label class="field-label" for="role-title">ROLE TITLE</label><input id="role-title" data-focus="role-title" class="text-input" value="${escapeHtml(state.title)}" placeholder="e.g. Backend Software Engineer" ${state.busy || state.job ? 'disabled' : ''}>
            <label class="field-label textarea-label" for="jd">JOB DESCRIPTION <span class="optional">PASTE TEXT</span></label><textarea id="jd" data-focus="jd" class="jd-textarea" placeholder="Paste the complete job description here…&#10;&#10;Include responsibilities, required skills, experience and qualifications." ${state.busy || state.job ? 'disabled' : ''}>${escapeHtml(state.jdText)}</textarea>
            <div class="input-footer"><label class="upload-inline ${state.jdFile ? 'file-selected' : ''}">${icon('upload')} ${state.jdFile ? escapeHtml(state.jdFile.name) : 'Or upload JD (PDF / DOCX)'}<input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" hidden data-input="jd-file" ${state.busy || state.job ? 'disabled' : ''}>${state.jdFile ? '<button type="button" class="clear-file" data-action="clear-jd" aria-label="Remove job description file">×</button>' : ''}</label><span class="char-count">${state.jdText.length} characters</span></div>
            ${renderRequirements()}
          </div>
          <div class="panel upload-panel">
            <div class="panel-heading"><div class="step-number">02</div><div><h2>Candidate resumes</h2><p>Upload a batch to compare against this role.</p></div>${icon('file', 'panel-icon')}</div>
            <label class="dropzone ${state.resumes.length ? 'has-files' : ''} ${state.dragging ? 'dragging' : ''}">
              <div class="drop-icon">${icon('download', '', 22)}</div><strong>${state.resumes.length ? `${state.resumes.length} resume(s) selected` : 'Drop resumes here or browse files'}</strong><span>PDF or DOCX · Up to 50 files · 10 MB each</span>
              <input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" multiple hidden data-input="resumes" ${state.busy || state.job ? 'disabled' : ''}>
              ${state.resumes.length ? `<div class="file-list-preview">${state.resumes.slice(0, 3).map(file => `<span>${escapeHtml(file.name)}</span>`).join('')}${state.resumes.length > 3 ? `<span>+${state.resumes.length - 3} more</span>` : ''}</div>` : ''}
            </label>
            <div class="upload-note">${icon('shield')}<span>Use synthetic or consented data. Uploaded files are stored locally in this prototype database.</span></div>
            <button class="button button-primary analyze-button" data-action="analyze" ${missingRequirements.length || state.busy ? 'disabled' : ''}>${state.busy ? `${icon('loader', 'spin')} Analyzing candidates…` : `${icon('sparkles')} Analyze &amp; rank candidates ${icon('chevron')}`}</button>
            ${missingRequirements.length ? `<div class="analyze-hint">To analyze, ${missingRequirements.join(' and ')}.</div>` : ''}
            <div class="privacy-caption">${icon('help')} Only extracted text and metadata are retained locally; original uploads are not stored. Scores are decision-support signals, not automated hiring decisions.</div>
          </div>
        </section>
        ${state.error ? `<div class="alert alert-error">${icon('close')}${escapeHtml(state.error)}</div>` : ''}
        ${state.notice ? `<div class="alert alert-success">${icon('checkCircle')}${escapeHtml(state.notice)}</div>` : ''}
        ${state.rejected.length ? `<div class="rejected-box"><strong>Files not processed</strong>${state.rejected.map(item => `<div><span>${escapeHtml(item.file_name)}</span><span>${escapeHtml(item.reason)}</span></div>`).join('')}</div>` : ''}
        ${state.job ? `
          <section class="metrics-grid">
            <div class="metric-card"><div class="metric-label">PROFILES ANALYZED</div><div class="metric-value">${state.results.length}<span class="metric-unit"> candidates</span></div><div class="metric-foot">For ${escapeHtml(state.job.title)}</div></div>
            <div class="metric-card"><div class="metric-label">TOP MATCH</div><div class="metric-value">${topScore.toFixed(1)}<span class="metric-unit">%</span></div><div class="metric-foot">Highest overall fit score</div></div>
            <div class="metric-card"><div class="metric-label">AVERAGE MATCH</div><div class="metric-value">${average.toFixed(1)}<span class="metric-unit">%</span></div><div class="metric-foot">Across analyzed candidates</div></div>
            <div class="metric-card"><div class="metric-label">AVG. SKILLS MATCHED</div><div class="metric-value">${avgSkills}<span class="metric-unit"> skills</span></div><div class="metric-foot">From identified JD skills</div></div>
          </section>
          <section class="results-section">
            <div class="results-heading"><div><div class="eyebrow">03 / SHORTLIST OVERVIEW</div><h2>Candidate ranking</h2><p>Ranked by explainable match score. Select a candidate to inspect the evidence.</p></div><div class="results-controls"><div class="search-box">${icon('search')}<input data-focus="search" value="${escapeHtml(state.search)}" placeholder="Search candidates or skills"></div><select class="sort-select" data-input="sort"><option value="score" ${state.sort === 'score' ? 'selected' : ''}>Sort: Match score</option><option value="experience" ${state.sort === 'experience' ? 'selected' : ''}>Sort: Experience</option><option value="name" ${state.sort === 'name' ? 'selected' : ''}>Sort: Name</option></select></div></div>
            <div class="table-wrap"><table><thead><tr><th class="rank-col">RANK</th><th>CANDIDATE</th><th>EXPERIENCE</th><th>MATCH SCORE</th><th>MATCHED SKILLS</th><th></th></tr></thead><tbody>${table.rows}</tbody></table></div>
            <div class="table-footer"><span>Showing ${visible.length} of ${state.results.length} candidates</span><span>Similarity engine: <strong>${escapeHtml(state.engine || 'loading')}</strong></span></div>
          </section>
          ${(state.selected !== null || state.detailBusy) ? `<section class="detail-section"><div class="detail-heading"><div><div class="eyebrow">04 / CANDIDATE DEEP DIVE</div><h2>Candidate analysis</h2><p>Evidence behind the score and extracted profile details.</p></div><button class="icon-button" data-action="close-detail" aria-label="Close candidate analysis">${icon('close')}</button></div>${state.detailBusy ? `<div class="detail-loading">${icon('loader', 'spin')} Loading candidate analysis…</div>` : renderDetail()}</section>` : ''}
        ` : ''}
        <footer class="footer"><div class="footer-brand">${icon('sparkles')} talentscope</div><span>Prototype · ResumeMatch AI · Human review required</span></footer>
      </main>
    </div>`;

  document.querySelector('[data-input="jd-file"]')?.addEventListener('change', event => {
    state.jdFile = event.currentTarget.files?.[0] || null;
    render();
  });
  document.querySelector('[data-input="resumes"]')?.addEventListener('change', event => {
    readFiles(event.currentTarget.files);
  });

  if (focusId) {
    const replacement = document.querySelector(`[data-focus="${focusId}"]`);
    if (replacement) {
      replacement.focus();
      if (selectionStart !== null && typeof replacement.setSelectionRange === 'function') {
        replacement.setSelectionRange(selectionStart, selectionEnd);
      }
    }
  }
}

function readFiles(fileList) {
  const selected = Array.from(fileList || []);
  const allowed = selected.filter(isSupportedDocument);
  state.error = allowed.length !== selected.length
    ? 'Only PDF and DOCX resumes are supported; unsupported files were skipped.'
    : '';
  if (allowed.length > 50) state.error = 'A maximum of 50 resumes can be uploaded in one batch. The first 50 were selected.';
  state.resumes = allowed.slice(0, 50);
  render();
}

async function readError(response) {
  try {
    const data = await response.json();
    return data.detail || data.message || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

async function analyze() {
  state.busy = true;
  state.error = '';
  state.notice = '';
  state.rejected = [];
  state.selected = null;
  state.detail = null;
  render();
  try {
    const jobForm = new FormData();
    jobForm.append('title', state.title);
    jobForm.append('jd_text', state.jdText);
    if (state.jdFile) jobForm.append('jd_file', state.jdFile);
    const jobResponse = await fetch(`${API}/api/jobs`, { method: 'POST', body: jobForm });
    if (!jobResponse.ok) throw new Error(await readError(jobResponse));
    const jobData = await jobResponse.json();

    const resumeForm = new FormData();
    state.resumes.forEach(file => resumeForm.append('files', file));
    const uploadResponse = await fetch(`${API}/api/jobs/${jobData.id}/resumes`, { method: 'POST', body: resumeForm });
    if (!uploadResponse.ok) throw new Error(await readError(uploadResponse));
    const uploadData = await uploadResponse.json();
    state.job = jobData;
    state.results = uploadData.accepted || [];
    state.rejected = uploadData.rejected || [];
    state.engine = uploadData.similarity_engine || '';
    state.notice = `${uploadData.accepted_count} resume(s) analyzed${uploadData.rejected_count ? ` · ${uploadData.rejected_count} file(s) could not be processed` : ''}.`;
    if (!uploadData.accepted_count) state.error = 'No resumes could be analyzed. Review the rejected file messages below.';
  } catch (error) {
    state.error = error.message || 'Something went wrong while analyzing the resumes.';
  } finally {
    state.busy = false;
    render();
  }
}

async function openCandidate(candidateId) {
  state.selected = candidateId;
  state.detail = null;
  state.detailBusy = true;
  render();
  try {
    const response = await fetch(`${API}/api/jobs/${state.job.id}/candidates/${candidateId}`);
    if (!response.ok) throw new Error(await readError(response));
    state.detail = await response.json();
  } catch (error) {
    state.error = error.message;
  } finally {
    state.detailBusy = false;
    render();
  }
}

function resetAnalysis() {
  Object.assign(state, {
    job: null, results: [], selected: null, detail: null, rejected: [],
    notice: '', error: '', resumes: [],
  });
  render();
}

document.addEventListener('input', event => {
  if (event.target.id === 'role-title') state.title = event.target.value;
  else if (event.target.id === 'jd') state.jdText = event.target.value;
  else if (event.target.matches('.search-box input')) state.search = event.target.value;
  render();
});

document.addEventListener('change', event => {
  if (event.target.dataset.input === 'sort') {
    state.sort = event.target.value;
    render();
  }
});

document.addEventListener('click', event => {
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (action === 'analyze') analyze();
  else if (action === 'reset') resetAnalysis();
  else if (action === 'clear-jd') {
    event.preventDefault();
    state.jdFile = null;
    render();
  } else if (action === 'close-detail') {
    state.selected = null;
    state.detail = null;
    render();
  } else {
    const row = event.target.closest('[data-candidate-id]');
    if (row) openCandidate(Number(row.dataset.candidateId));
  }
});

document.addEventListener('dragover', event => {
  if (event.target.closest('.dropzone')) {
    event.preventDefault();
    if (!state.dragging) {
      state.dragging = true;
      document.querySelector('.dropzone')?.classList.add('dragging');
    }
  }
});

document.addEventListener('dragleave', event => {
  if (event.target.closest('.dropzone') && !event.target.closest('.dropzone').contains(event.relatedTarget)) {
    state.dragging = false;
    document.querySelector('.dropzone')?.classList.remove('dragging');
  }
});

document.addEventListener('drop', event => {
  const dropzone = event.target.closest('.dropzone');
  if (!dropzone) return;
  event.preventDefault();
  state.dragging = false;
  readFiles(event.dataTransfer.files);
});

render();
