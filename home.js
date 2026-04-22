// Home page logic

(async () => {
  await App.loadData();
  App.loadProgress();
  const counts = App.getCounts();
  animateCount(document.getElementById('dueCount'), counts.due, 600);
  animateCount(document.getElementById('newCount'), counts.new, 500);
  animateCount(document.getElementById('totalCount'), counts.total, 700);
  animateCount(document.getElementById('streak'), counts.streak, 500);

  const articles = App.data.articles || [];
  const p = App.loadProgress();
  const favoriteIds = new Set(Object.keys(p.favoriteArticles || {}));

  const favorites = articles.filter(a => favoriteIds.has(a.id));
  const studying = articles.filter(a => a.status !== 'finished' && !favoriteIds.has(a.id));
  const finished = articles.filter(a => a.status === 'finished' && !favoriteIds.has(a.id));

  if (favorites.length) {
    document.getElementById('favoritesSection').hidden = false;
    document.getElementById('favoritesList').innerHTML = favorites.map(renderArticleCard).join('');
  }

  const studyingEl = document.getElementById('studyingList');
  studyingEl.innerHTML = studying.length
    ? studying.map(renderArticleCard).join('')
    : '<p class="muted">还没有文章。发给 Claude 添加第一篇。</p>';

  if (finished.length) {
    document.getElementById('finishedSection').hidden = false;
    document.getElementById('finishedList').innerHTML = finished.map(renderArticleCard).join('');
  }

  function renderArticleCard(a) {
    const sents = App.data.sentences.filter(s => (s.article_id || s.video_id) === a.id).length;
    const highlights = App.data.sentences.filter(s => (s.article_id || s.video_id) === a.id && s.is_highlight).length;
    const typeIcon = { youtube: '▶', audio: '🎵', text: '📄' }[a.type] || '📖';
    const typeClass = { youtube: 'type-youtube', audio: 'type-audio', text: 'type-text' }[a.type] || 'type-default';
    const statusBadge = a.status === 'finished' ? '<span class="badge-finished">已学完</span>' : '';
    const duration = a.duration_str ? ` · ${a.duration_str}` : '';
    return `
      <a class="video-card video-card-link" href="reader.html?a=${encodeURIComponent(a.id)}">
        <div class="card-type-badge ${typeClass}">${typeIcon}</div>
        <div class="card-body">
          <div class="title">${escapeHtml(a.title || a.id)} ${statusBadge}</div>
          <div class="meta"><b>${sents}</b> 句 · <b>${highlights}</b> 重点${duration}</div>
        </div>
        <div class="video-card-arrow">→</div>
      </a>
    `;
  }

})();

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function animateCount(el, target, duration = 600) {
  if (!el) return;
  const n = Number(target) || 0;
  if (n <= 0) { el.textContent = n; return; }
  const start = performance.now();
  function tick(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(n * eased);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
