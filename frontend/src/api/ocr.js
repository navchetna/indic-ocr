// ── API service layer for IndicOCR backend ────────────────────
const API_BASE = '/api';
const OUTPUTS_BASE = '/outputs';

/**
 * POST /ocr/single — upload a single image for OCR
 */
export async function submitSingleOCR(file, lang, saveAnnotated = true) {
  const formData = new FormData();
  formData.append('file', file);

  const params = new URLSearchParams({ lang, save_annotated: saveAnnotated });
  const res = await fetch(`${API_BASE}/ocr/single?${params}`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'OCR request failed');
  }
  return res.json();
}

/**
 * GET /ocr/languages — fetch supported languages
 */
export async function fetchLanguages() {
  const res = await fetch(`${API_BASE}/ocr/languages`);
  if (!res.ok) throw new Error('Failed to fetch languages');
  return res.json();
}

/**
 * GET /health — check backend health
 */
export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Backend unreachable');
  return res.json();
}

/**
 * List recent tasks by scanning the output directory via nginx autoindex (JSON).
 * Returns sorted (newest-first) array of task objects.
 */
export async function listRecentTasks(mode = 'single', limit = 10) {
  const tasks = [];

  // Scan all language subdirectories
  const langDirs = await fetchDirListing(`${OUTPUTS_BASE}/${mode}/`);
  if (!langDirs) return tasks;

  for (const langEntry of langDirs) {
    if (langEntry.type !== 'directory') continue;
    const lang = langEntry.name;

    const taskDirs = await fetchDirListing(`${OUTPUTS_BASE}/${mode}/${lang}/`);
    if (!taskDirs) continue;

    for (const taskEntry of taskDirs) {
      if (taskEntry.type !== 'directory') continue;
      tasks.push({
        id: `${mode}/${lang}/${taskEntry.name}`,
        lang,
        dirName: taskEntry.name,
        mode,
        mtime: taskEntry.mtime || taskEntry.name, // fallback sort key
        path: `${OUTPUTS_BASE}/${mode}/${lang}/${taskEntry.name}`,
      });
    }
  }

  // Sort by dirname (YYYYMMDD_HHMMSS prefix) descending
  tasks.sort((a, b) => b.dirName.localeCompare(a.dirName));
  return tasks.slice(0, limit);
}

/**
 * Fetch result.json for a specific task
 */
export async function fetchTaskResult(taskPath) {
  const res = await fetch(`${taskPath}/result.json`);
  if (!res.ok) throw new Error('Failed to load task result');
  return res.json();
}

/**
 * Find the annotated image filename in a task directory.
 */
export async function findAnnotatedImage(taskPath) {
  const files = await fetchDirListing(`${taskPath}/`);
  if (!files) return null;

  const imgEntry = files.find(
    (f) =>
      f.type === 'file' &&
      (f.name.includes('ocr_res_img') || f.name.includes('_res_img'))
  );

  return imgEntry ? `${taskPath}/${imgEntry.name}` : null;
}

/**
 * Fetch a batch summary
 */
export async function fetchBatchSummary(taskPath) {
  const res = await fetch(`${taskPath}/batch_summary.json`);
  if (!res.ok) throw new Error('Failed to load batch summary');
  return res.json();
}

// ── Helper: nginx autoindex JSON ────────────────────────────
async function fetchDirListing(dirUrl) {
  try {
    const res = await fetch(dirUrl);
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data : null;
  } catch {
    return null;
  }
}
