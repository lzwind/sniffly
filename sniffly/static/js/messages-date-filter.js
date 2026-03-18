/**
 * Messages Date Filter
 * Date range filtering state and utilities for the Messages tab.
 * Must be loaded before messages-tab.js.
 */

const MS_PER_DAY = 86400000; // milliseconds in one day

// Date filter state — var so they are visible across scripts in the same page
var dateFilterPreset = 'today'; // 'today' | 'yesterday' | '7days' | '30days' | 'all' | 'custom'
var dateFilterStart = null;     // Date object, inclusive
var dateFilterEnd = null;       // Date object, inclusive (end of day)

/** Compute start/end Date objects for a named preset */
function getDateRangeForPreset(preset) {
  const now = new Date();
  // Local midnight of today
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const todayEnd = new Date(today.getTime() + MS_PER_DAY - 1);

  switch (preset) {
    case 'today':
      return { start: today, end: todayEnd };
    case 'yesterday': {
      const yest = new Date(today.getTime() - MS_PER_DAY);
      return { start: yest, end: new Date(today.getTime() - 1) };
    }
    case '7days':
      return { start: new Date(today.getTime() - 6 * MS_PER_DAY), end: todayEnd };
    case '30days':
      return { start: new Date(today.getTime() - 29 * MS_PER_DAY), end: todayEnd };
    case 'all':
    default:
      return { start: null, end: null };
  }
}

/** Sync custom date inputs to reflect the given range */
function syncCustomDateInputs(range) {
  const fmt = (d) => {
    if (!d) { return ''; }
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };
  const startEl = document.getElementById('date-filter-start');
  const endEl = document.getElementById('date-filter-end');
  if (startEl) { startEl.value = fmt(range.start); }
  if (endEl) { endEl.value = fmt(range.end || new Date()); }
}

/** Activate a date preset button and reload from backend */
function setDatePreset(preset) {
  dateFilterPreset = preset;
  const range = getDateRangeForPreset(preset);
  dateFilterStart = range.start;
  dateFilterEnd = range.end;

  document.querySelectorAll('.date-preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === preset);
  });

  if (preset !== 'custom') {
    syncCustomDateInputs(range);
  }

  // reloadMessagesFromBackend is defined in messages-tab.js
  reloadMessagesFromBackend();
}

/** Called when user manually edits the custom date inputs */
function applyCustomDateFilter() {
  const startEl = document.getElementById('date-filter-start');
  const endEl = document.getElementById('date-filter-end');
  if (!startEl || !endEl) { return; }

  const startVal = startEl.value;
  const endVal = endEl.value;

  if (startVal) {
    const [y, m, d] = startVal.split('-').map(Number);
    dateFilterStart = new Date(y, m - 1, d);
  } else {
    dateFilterStart = null;
  }

  if (endVal) {
    const [y, m, d] = endVal.split('-').map(Number);
    dateFilterEnd = new Date(y, m - 1, d, 23, 59, 59, 999);
  } else {
    dateFilterEnd = null;
  }

  dateFilterPreset = 'custom';
  document.querySelectorAll('.date-preset-btn').forEach(btn => btn.classList.remove('active'));

  reloadMessagesFromBackend();
}

/** Returns true when a date-range filter is currently active */
function hasDateFilter() {
  return dateFilterPreset !== 'all' && (dateFilterStart !== null || dateFilterEnd !== null);
}

/** Format a Date object as YYYY-MM-DD for API query params */
function formatDateForApi(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Build /api/messages URL with current date filter + optional limit */
function buildMessagesApiUrl(limit) {
  const params = new URLSearchParams();
  const tzOffset = -new Date().getTimezoneOffset(); // e.g. +480 for UTC+8
  params.set('timezone_offset', tzOffset);

  if (dateFilterPreset !== 'all' && dateFilterStart) {
    params.set('start_date', formatDateForApi(dateFilterStart));
  }
  if (dateFilterPreset !== 'all' && dateFilterEnd) {
    params.set('end_date', formatDateForApi(dateFilterEnd));
  }
  if (limit) {
    params.set('limit', limit);
  }
  return `/api/messages?${params.toString()}`;
}
