const assert = require('node:assert/strict');
const test = require('node:test');
const { badgeStatus, escapeHtml } = require('../../mobile_console/static/dashboard_helpers.js');

test('escapeHtml escapes HTML-sensitive characters', () => {
  assert.equal(escapeHtml('<img src=x onerror=alert(1)>'), '&lt;img src=x onerror=alert(1)&gt;');
  assert.equal(escapeHtml('"quoted" & \'single\''), '&quot;quoted&quot; &amp; &#39;single&#39;');
});

test('badgeStatus normalizes and escapes status labels', () => {
  assert.equal(badgeStatus(' validated '), '<span class="badge badge-ok">VALIDATED</span>');
  assert.equal(badgeStatus('<script>'), '<span class="badge badge-queued">&lt;SCRIPT&gt;</span>');
});
