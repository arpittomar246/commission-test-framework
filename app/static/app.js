/* Shared helpers for the portal pages: API access, toasts, modals, formatting.
   Kept deliberately small and dependency-free -- no build step, no framework. */

const API = {
  async request(method, path, body) {
    const options = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) options.body = JSON.stringify(body);
    const response = await fetch(path, options);
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const err = new Error((data && data.detail) || 'Request failed');
      err.status = response.status;
      err.code = (data && data.code) || 'UNKNOWN';
      throw err;
    }
    return data;
  },
  get: (path) => API.request('GET', path),
  post: (path, body) => API.request('POST', path, body),
};

const fmtMoney = (n) =>
  Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const fmtDate = (iso) => (iso ? iso : '--');

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );

/* ---------------------------------------------------------------- toasts -- */

function toast(message, kind = 'success') {
  const container = document.querySelector('[data-testid="toast-container"]');
  const el = document.createElement('div');
  const tone =
    kind === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : 'border-red-200 bg-red-50 text-red-800';
  el.className = `pointer-events-auto rounded-lg border px-4 py-3 text-sm font-medium shadow-sm ${tone}`;
  el.setAttribute('data-testid', kind === 'success' ? 'toast-success' : 'toast-error');
  el.setAttribute('role', 'status');
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

/* ---------------------------------------------------------------- modals -- */

function openModal(testid) {
  const modal = document.querySelector(`[data-testid="${testid}"]`);
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  modal.setAttribute('data-open', 'true');
}

function closeModal(testid) {
  const modal = document.querySelector(`[data-testid="${testid}"]`);
  modal.classList.add('hidden');
  modal.classList.remove('flex');
  modal.setAttribute('data-open', 'false');
  modal.querySelectorAll('[data-error]').forEach((n) => {
    n.textContent = '';
    n.classList.add('hidden');
  });
}

function showFieldError(testid, message) {
  const el = document.querySelector(`[data-testid="${testid}"]`);
  el.textContent = message;
  el.classList.remove('hidden');
}

function clearFieldErrors(scopeTestid) {
  document
    .querySelector(`[data-testid="${scopeTestid}"]`)
    .querySelectorAll('[data-error]')
    .forEach((n) => {
      n.textContent = '';
      n.classList.add('hidden');
    });
}

/* ---------------------------------------------------------------- badges -- */

function statusBadge(status, testid) {
  const tone =
    status === 'active'
      ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
      : 'bg-red-50 text-red-700 ring-red-200';
  const label = status === 'active' ? 'Active' : 'Cancelled';
  return `<span data-testid="${testid}" data-status="${status}"
    class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${tone}">${label}</span>`;
}

function guaranteeBadge(active, testid) {
  const tone = active
    ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
    : 'bg-slate-100 text-slate-500 ring-slate-200';
  const label = active ? 'Guarantee Active' : 'Guarantee Expired';
  return `<span data-testid="${testid}" data-guarantee="${active ? 'active' : 'expired'}"
    class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${tone}">${label}</span>`;
}

/* ------------------------------------------------------------- utilities -- */

function show(testid) {
  document.querySelector(`[data-testid="${testid}"]`).classList.remove('hidden');
}

function hide(testid) {
  document.querySelector(`[data-testid="${testid}"]`).classList.add('hidden');
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function currentMonth() {
  return new Date().toISOString().slice(0, 7);
}
