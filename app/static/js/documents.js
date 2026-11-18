/**
 * SafeSight AI - Milestone 2: Documents & Repositories Frontend Logic
 */

let selectedFiles = [];
let searchDebounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  // If on documents overview page
  if (document.getElementById('docsTableBody')) {
    fetchDocuments();
    fetchStats();
  }

  // Setup Drag & Drop if on upload page
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  if (dropZone && fileInput) {
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--accent)';
      dropZone.style.background = 'rgba(249, 115, 22, 0.05)';
    });

    dropZone.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--border-color)';
      dropZone.style.background = 'var(--bg-surface-alt)';
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--border-color)';
      dropZone.style.background = 'var(--bg-surface-alt)';
      if (e.dataTransfer.files.length) {
        handleFilesSelected(e.dataTransfer.files);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) {
        handleFilesSelected(fileInput.files);
      }
    });
  }

  // Render procedure steps if present on detail page
  document.querySelectorAll('.procedure-steps-box').forEach(box => {
    try {
      const raw = box.getAttribute('data-steps');
      const steps = JSON.parse(raw);
      if (Array.isArray(steps)) {
        let html = '<ol style="padding-left: 20px; margin: 0; line-height: 1.6; font-size: 13px;">';
        steps.forEach(st => {
          html += `<li style="margin-bottom: 6px;">${escapeHtml(st)}</li>`;
        });
        html += '</ol>';
        box.innerHTML = html;
      }
    } catch (e) {}
  });
});

/* --------------------------------------------------------------------------
   Documents Library Page
   -------------------------------------------------------------------------- */

function fetchDocuments() {
  const repo = document.getElementById('filterRepo')?.value || 'all';
  const type = document.getElementById('filterType')?.value || 'all';
  const status = document.getElementById('filterStatus')?.value || 'all';
  const q = document.getElementById('docSearchInput')?.value || '';

  const tbody = document.getElementById('docsTableBody');
  if (!tbody) return;

  fetch(`/api/documents?repository_id=${repo}&type=${type}&status=${status}&q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => {
      renderDocumentsTable(data.documents || []);
    })
    .catch(err => {
      tbody.innerHTML = `<tr><td colspan="8" style="padding: 24px; text-align: center; color: var(--danger);">Failed to load documents: ${err.message}</td></tr>`;
    });
}

function debounceSearch() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(fetchDocuments, 300);
}

function fetchStats() {
  fetch('/api/knowledge/stats')
    .then(r => r.json())
    .then(d => {
      if (document.getElementById('kpiTotalDocs')) document.getElementById('kpiTotalDocs').innerText = d.total_documents;
      if (document.getElementById('kpiProcessedDocs')) document.getElementById('kpiProcessedDocs').innerText = d.processed_documents;
      if (document.getElementById('kpiReviewDocs')) document.getElementById('kpiReviewDocs').innerText = d.needs_review;
      if (document.getElementById('kpiFindings')) document.getElementById('kpiFindings').innerText = d.total_findings;
      if (document.getElementById('kpiOpenFindings')) document.getElementById('kpiOpenFindings').innerText = `${d.open_findings} Open Infractions`;
    })
    .catch(() => {});
}

function renderDocumentsTable(docs) {
  const tbody = document.getElementById('docsTableBody');
  if (!tbody) return;

  if (docs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="padding: 48px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 32px; margin-bottom: 8px;">📂</div>
          <p style="font-size: 14px; font-weight: 600; margin-bottom: 4px;">No documents match the current filters</p>
          <p style="font-size: 12px; margin: 0;">Upload site reports or safety manuals to populate the library.</p>
        </td>
      </tr>
    `;
    return;
  }

  let rows = '';
  docs.forEach(doc => {
    const icon = doc.doc_type === 'inspection_report' ? '📋' : (doc.doc_type === 'safety_manual' ? '📖' : '📄');
    const typeLabel = (doc.doc_type || 'other').replace('_', ' ').toUpperCase();
    const statusClass = `status-${(doc.status || 'uploaded').replace(' ', '-')}`;

    let contentInfo = '';
    if (doc.doc_type === 'inspection_report') {
      contentInfo = `${doc.findings_count || 0} findings`;
    } else {
      contentInfo = `${doc.rules_count || 0} rules`;
    }

    rows += `
      <tr style="border-bottom: 1px solid var(--border-color); transition: background 0.15s;" onmouseover="this.style.background='var(--bg-surface-alt)'" onmouseout="this.style.background='transparent'">
        <td style="padding: 14px 20px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 20px;">${icon}</span>
            <div>
              <a href="/documents/${doc.id}" style="font-weight: 700; color: var(--text-main); text-decoration: none;">${escapeHtml(doc.title)}</a>
              <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(doc.original_name)}</div>
            </div>
          </div>
        </td>
        <td style="padding: 14px 16px;">
          <span style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: var(--bg-surface-alt); border: 1px solid var(--border-color);">${typeLabel}</span>
        </td>
        <td style="padding: 14px 16px; color: var(--text-muted);">${escapeHtml(doc.repository_name || 'General')}</td>
        <td style="padding: 14px 16px; font-weight: 600;">${doc.page_count}</td>
        <td style="padding: 14px 16px; font-size: 12px; color: var(--text-muted);">${contentInfo}</td>
        <td style="padding: 14px 16px;">
          <span class="status-pill ${statusClass}" style="font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 10px; text-transform: uppercase;">
            ${doc.status}
          </span>
        </td>
        <td style="padding: 14px 16px; font-size: 12px; color: var(--text-muted);">${doc.uploaded_at ? doc.uploaded_at.substring(0, 10) : ''}</td>
        <td style="padding: 14px 20px; text-align: right;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <a href="/documents/${doc.id}" class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px;">Open</a>
            <button onclick="deleteDoc(${doc.id})" class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px; color: var(--danger);">✕</button>
          </div>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = rows;
}

function loadDemoDocuments() {
  const btn = document.getElementById('btnLoadDemoDocs');
  if (btn) btn.innerText = 'Loading demo data...';

  fetch('/api/seed-documents', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      showToast(d.message || 'Demo documents loaded successfully!', 'success');
      setTimeout(() => location.reload(), 800);
    })
    .catch(err => {
      showToast('Error loading demo documents: ' + err.message, 'error');
      if (btn) btn.innerText = 'Load Demo Documents';
    });
}

function deleteDoc(docId) {
  if (!confirm('Are you sure you want to delete this document and its indexed chunks?')) return;

  fetch(`/api/documents/${docId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(() => {
      showToast('Document deleted.', 'info');
      if (document.getElementById('docsTableBody')) {
        fetchDocuments();
        fetchStats();
      } else {
        window.location.href = '/documents';
      }
    })
    .catch(err => showToast(err.message, 'error'));
}

function reprocessDoc(docId) {
  fetch(`/api/documents/${docId}/reprocess`, { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      showToast('Reprocessing started.', 'info');
      setTimeout(() => location.reload(), 1000);
    });
}

function verifyDoc(docId) {
  fetch(`/api/documents/${docId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'verified' })
  })
    .then(r => r.json())
    .then(() => {
      showToast('Document verified.', 'success');
      setTimeout(() => location.reload(), 500);
    });
}

/* --------------------------------------------------------------------------
   Upload & Pipeline Tracker Page
   -------------------------------------------------------------------------- */

function handleFilesSelected(files) {
  selectedFiles = Array.from(files);
  const container = document.getElementById('selectedFilesContainer');
  const list = document.getElementById('fileList');
  const count = document.getElementById('fileCount');

  if (!container || !list) return;

  container.style.display = 'block';
  count.innerText = selectedFiles.length;

  let html = '';
  selectedFiles.forEach((f, idx) => {
    const sizeMb = (f.size / (1024 * 1024)).toFixed(2);
    html += `
      <div style="background: var(--bg-surface-alt); border: 1px solid var(--border-color); padding: 8px 14px; border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
        <span><strong>${escapeHtml(f.name)}</strong> (${sizeMb} MB)</span>
        <button type="button" onclick="removeSelectedFile(${idx})" style="background: none; border: none; color: var(--danger); cursor: pointer; font-weight: bold;">✕</button>
      </div>
    `;
  });
  list.innerHTML = html;
}

function removeSelectedFile(index) {
  selectedFiles.splice(index, 1);
  handleFilesSelected(selectedFiles);
  if (selectedFiles.length === 0) {
    document.getElementById('selectedFilesContainer').style.display = 'none';
  }
}

function clearSelectedFiles() {
  selectedFiles = [];
  document.getElementById('selectedFilesContainer').style.display = 'none';
  document.getElementById('fileInput').value = '';
}

function uploadAndProcessFiles() {
  if (selectedFiles.length === 0) return;

  const btn = document.getElementById('btnStartProcessing');
  btn.disabled = true;
  btn.innerText = 'Uploading...';

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append('files', f));

  const repo = document.getElementById('uploadRepoSelect')?.value;
  if (repo) formData.append('repository_id', repo);

  const docType = document.getElementById('uploadDocTypeSelect')?.value;
  if (docType) formData.append('doc_type', docType);

  fetch('/api/documents/upload', {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);

      showToast(`Uploaded ${data.count} document(s). Processing started.`, 'success');
      document.getElementById('selectedFilesContainer').style.display = 'none';
      document.getElementById('pipelineTrackerCard').style.display = 'block';

      trackPipeline(data.documents);
    })
    .catch(err => {
      showToast('Upload error: ' + err.message, 'error');
      btn.disabled = false;
      btn.innerText = 'Process Documents';
    });
}

function trackPipeline(docs) {
  const container = document.getElementById('trackerList');
  if (!container) return;

  let html = '';
  docs.forEach(d => {
    html += `
      <div id="tracker_${d.id}" style="background: var(--bg-surface-alt); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="font-weight: 700; font-size: 14px;">${escapeHtml(d.title)}</span>
          <span id="step_${d.id}" style="font-size: 12px; color: var(--info); font-weight: 600;">Starting pipeline...</span>
        </div>
        <div style="background: var(--border-color); height: 8px; border-radius: 4px; overflow: hidden;">
          <div id="bar_${d.id}" style="width: 10%; height: 100%; background: var(--accent); transition: width 0.4s ease;"></div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;

  // Poll progress every second
  const pollInterval = setInterval(() => {
    let allDone = true;

    Promise.all(docs.map(d => fetch(`/api/documents/${d.id}/progress`).then(r => r.json())))
      .then(statuses => {
        statuses.forEach((st, i) => {
          const docId = docs[i].id;
          const bar = document.getElementById(`bar_${docId}`);
          const step = document.getElementById(`step_${docId}`);

          if (bar) bar.style.width = `${st.progress || 10}%`;
          if (step) {
            step.innerText = st.step || st.status;
            if (st.status === 'processed' || st.status === 'verified') {
              step.style.color = 'var(--safe)';
              step.innerHTML = '✅ Done &bull; <a href="/documents/' + docId + '" style="color: var(--accent); text-decoration: underline;">View</a>';
            } else if (st.status === 'failed') {
              step.style.color = 'var(--danger)';
              step.innerText = '❌ Failed: ' + (st.error || 'Unknown error');
            } else {
              allDone = false;
            }
          }
        });

        if (allDone) {
          clearInterval(pollInterval);
          showToast('All documents processed successfully!', 'success');
        }
      })
      .catch(() => {});
  }, 1000);
}

/* --------------------------------------------------------------------------
   Document Detail Page Helpers
   -------------------------------------------------------------------------- */

function renderSelectedPage() {
  const pageNo = parseInt(document.getElementById('pageSelect').value, 10);
  const display = document.getElementById('pageContentDisplay');
  if (!display || typeof PAGE_DATA === 'undefined') return;

  const p = PAGE_DATA.find(x => x.page_no === pageNo);
  display.innerText = p ? p.text : '(Page empty)';
}

function jumpToPage(pageNo) {
  const sel = document.getElementById('pageSelect');
  if (sel) {
    sel.value = pageNo;
    renderSelectedPage();
  }
}

function switchDetailTab(tabName, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.detail-tab-pane').forEach(p => p.style.display = 'none');

  if (btn) btn.classList.add('active');
  const targetId = 'tab' + tabName.charAt(0).toUpperCase() + tabName.slice(1);
  const pane = document.getElementById(targetId);
  if (pane) pane.style.display = 'block';
}

function saveFieldEdit(docId, fieldId) {
  const val = document.getElementById(`fieldVal_${fieldId}`).value;
  fetch(`/api/documents/${docId}/fields/${fieldId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value: val })
  })
    .then(r => r.json())
    .then(() => showToast('Field updated and tagged as edited.', 'success'))
    .catch(e => showToast(e.message, 'error'));
}

function toggleFindingStatus(docId, findingId, curStatus) {
  const newStatus = curStatus === 'closed' ? 'open' : 'closed';
  fetch(`/api/documents/${docId}/findings/${findingId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus })
  })
    .then(r => r.json())
    .then(() => {
      showToast(`Finding marked as ${newStatus}.`, 'success');
      setTimeout(() => location.reload(), 400);
    });
}

function changeDocRepo(docId, newRepoId) {
  fetch(`/api/documents/${docId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repository_id: newRepoId ? parseInt(newRepoId) : null })
  })
    .then(r => r.json())
    .then(() => showToast('Document moved to repository.', 'success'));
}

/* --------------------------------------------------------------------------
   Repositories Page Helpers
   -------------------------------------------------------------------------- */

function fetchRepositoriesList() {
  const grid = document.getElementById('repositoriesGrid');
  if (!grid) return;

  fetch('/api/repositories')
    .then(r => r.json())
    .then(data => {
      renderRepositoriesGrid(data.repositories || []);
    });
}

function renderRepositoriesGrid(repos) {
  const grid = document.getElementById('repositoriesGrid');
  if (!grid) return;

  let html = '';
  repos.forEach(r => {
    html += `
      <div class="card" style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; gap: 16px;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
            <h3 style="font-size: 18px; font-weight: 800; margin: 0;">${escapeHtml(r.name)}</h3>
            <span style="font-size: 12px; font-weight: 700; background: var(--bg-surface-alt); border: 1px solid var(--border-color); padding: 2px 8px; border-radius: 4px;">
              ${r.doc_count || 0} Docs
            </span>
          </div>
          <p style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin: 0;">${escapeHtml(r.description || 'No description provided.')}</p>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 14px;">
          <a href="/documents?repository_id=${r.id}" class="btn btn-secondary" style="font-size: 12px; padding: 6px 12px;">Browse Documents</a>
          <button onclick="deleteRepository(${r.id})" class="btn btn-secondary" style="font-size: 12px; padding: 6px 10px; color: var(--danger);">Delete</button>
        </div>
      </div>
    `;
  });

  grid.innerHTML = html;
}

function openNewRepoModal() {
  document.getElementById('modalTitle').innerText = 'Create New Repository';
  document.getElementById('editRepoId').value = '';
  document.getElementById('repoNameInput').value = '';
  document.getElementById('repoDescInput').value = '';
  document.getElementById('repoModal').style.display = 'flex';
}

function closeRepoModal() {
  document.getElementById('repoModal').style.display = 'none';
}

function saveRepository() {
  const name = document.getElementById('repoNameInput').value.trim();
  const desc = document.getElementById('repoDescInput').value.trim();
  if (!name) return alert('Repository name is required');

  fetch('/api/repositories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, description: desc })
  })
    .then(r => r.json())
    .then(() => {
      closeRepoModal();
      showToast('Repository created.', 'success');
      fetchRepositoriesList();
    });
}

function deleteRepository(repoId) {
  if (!confirm('Are you sure you want to delete this repository? (Contained documents will remain safe in General)')) return;

  fetch(`/api/repositories/${repoId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(() => {
      showToast('Repository removed.', 'info');
      fetchRepositoriesList();
    });
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
