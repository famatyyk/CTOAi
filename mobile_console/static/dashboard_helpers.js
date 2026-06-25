(function attachDashboardHelpers(root) {
  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function badgeStatus(s) {
    const normalized = String(s || '').trim().toUpperCase();
    const map = { VALIDATED:'ok', GENERATED:'ok', READY:'ok', INGESTED:'waiting', SCOUTING:'waiting',
                  FAILED:'error', ERROR:'error', QUEUED:'queued', RELEASED:'ok', NEW:'queued' };
    const cls = map[normalized] || 'queued';
    return `<span class="badge badge-${cls}">${escapeHtml(normalized || 'UNKNOWN')}</span>`;
  }

  root.escapeHtml = escapeHtml;
  root.badgeStatus = badgeStatus;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { escapeHtml, badgeStatus };
  }
})(typeof globalThis !== 'undefined' ? globalThis : window);
