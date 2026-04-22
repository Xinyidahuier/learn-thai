// Cross-device progress sync via a private GitHub Gist.
// Token + gist ID live in localStorage; never committed.
// On page load: pull remote, replace local if remote is newer.
// On saveProgress: debounce 3s then push.

const Sync = {
  TOKEN_KEY: 'learn-thai-github-token',
  GIST_ID_KEY: 'learn-thai-gist-id',
  SYNCED_AT_KEY: 'learn-thai-synced-at',
  PROGRESS_KEY: 'learn-thai-progress-v1',
  FILE_NAME: 'learn-thai-progress.json',
  GIST_DESCRIPTION: 'Learn Thai · progress sync',

  getToken()   { return localStorage.getItem(this.TOKEN_KEY); },
  setToken(t)  { localStorage.setItem(this.TOKEN_KEY, t); },
  clearToken() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.GIST_ID_KEY);
    localStorage.removeItem(this.SYNCED_AT_KEY);
  },
  getGistId()   { return localStorage.getItem(this.GIST_ID_KEY); },
  setGistId(id) { localStorage.setItem(this.GIST_ID_KEY, id); },
  getLocalSyncedAt() { return Number(localStorage.getItem(this.SYNCED_AT_KEY)) || 0; },
  setLocalSyncedAt(t) { localStorage.setItem(this.SYNCED_AT_KEY, String(t)); },

  isEnabled() { return !!this.getToken(); },

  _headers() {
    return {
      'Authorization': `Bearer ${this.getToken()}`,
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json',
    };
  },

  async _pull() {
    const gistId = this.getGistId();
    if (!gistId) return null;
    const r = await fetch(`https://api.github.com/gists/${gistId}`, {
      headers: this._headers(),
      cache: 'no-cache',
    });
    if (!r.ok) throw new Error(`pull ${r.status}`);
    const gist = await r.json();
    const file = gist.files && gist.files[this.FILE_NAME];
    if (!file) return null;
    return JSON.parse(file.content);
  },

  // Scan the account's gists to find a pre-existing sync gist.
  // Called on a fresh device so we don't create a second gist.
  // If multiple match, pick the one with the newest syncedAt in its content
  // (protects against earlier versions that could duplicate-seed).
  async _findExistingGist() {
    const r = await fetch('https://api.github.com/gists?per_page=100', {
      headers: this._headers(),
      cache: 'no-cache',
    });
    if (!r.ok) throw new Error(`list ${r.status}`);
    const list = await r.json();
    const matches = list.filter(g =>
      g.description === this.GIST_DESCRIPTION &&
      g.files && g.files[this.FILE_NAME]
    );
    if (!matches.length) return null;
    if (matches.length === 1) return matches[0].id;

    let bestId = null, bestScore = -1;
    for (const g of matches) {
      try {
        const rr = await fetch(`https://api.github.com/gists/${g.id}`, {
          headers: this._headers(),
          cache: 'no-cache',
        });
        if (!rr.ok) continue;
        const gg = await rr.json();
        const file = gg.files && gg.files[this.FILE_NAME];
        if (!file) continue;
        const parsed = JSON.parse(file.content);
        const p = parsed.progress || {};
        // Score = total amount of real progress data. Prefer the non-empty gist
        // when duplicates exist.
        const score =
          Object.keys(p.savedVocab || {}).length +
          Object.keys(p.savedSentences || {}).length +
          Object.keys(p.cardStates || {}).length +
          Object.keys(p.articleStatus || {}).length +
          Object.keys(p.favoriteArticles || {}).length;
        if (score > bestScore) { bestScore = score; bestId = g.id; }
      } catch {}
    }
    return bestId || matches[0].id;
  },

  async _push(progress) {
    const body = { progress, syncedAt: Date.now() };
    const content = JSON.stringify(body, null, 2);
    const files = { [this.FILE_NAME]: { content } };
    const gistId = this.getGistId();

    if (!gistId) {
      const r = await fetch('https://api.github.com/gists', {
        method: 'POST',
        headers: this._headers(),
        body: JSON.stringify({
          description: this.GIST_DESCRIPTION,
          public: false,
          files,
        }),
      });
      if (!r.ok) throw new Error(`create ${r.status}`);
      const gist = await r.json();
      this.setGistId(gist.id);
    } else {
      const r = await fetch(`https://api.github.com/gists/${gistId}`, {
        method: 'PATCH',
        headers: this._headers(),
        body: JSON.stringify({ files }),
      });
      if (!r.ok) throw new Error(`push ${r.status}`);
    }
    this.setLocalSyncedAt(body.syncedAt);
    return body.syncedAt;
  },

  _pushTimer: null,
  _pushing: false,
  schedulePush() {
    if (!this.isEnabled()) return;
    clearTimeout(this._pushTimer);
    this._pushTimer = setTimeout(async () => {
      if (this._pushing) return;
      this._pushing = true;
      try {
        await this._push(App.progress);
      } catch (err) {
        console.warn('[sync] push failed:', err.message);
      } finally {
        this._pushing = false;
      }
    }, 3000);
  },

  // Called on page load. Pulls remote and resolves with local by timestamp.
  async start() {
    if (!this.isEnabled()) return { status: 'disabled' };
    // Ensure App.progress is hydrated from localStorage before comparing.
    App.loadProgress();
    try {
      // Fresh device: try to discover an existing sync gist first so we don't
      // create a duplicate and overwrite it with empty local progress.
      if (!this.getGistId()) {
        const found = await this._findExistingGist();
        if (found) this.setGistId(found);
      }

      const remote = await this._pull();
      const localTs = this.getLocalSyncedAt();

      if (!remote) {
        // No gist or empty — seed from local
        await this._push(App.progress);
        return { status: 'seeded' };
      }

      const remoteTs = remote.syncedAt || 0;
      if (remoteTs > localTs) {
        // Remote is newer — replace local (write directly to avoid re-push loop)
        App.progress = remote.progress;
        localStorage.setItem(this.PROGRESS_KEY, JSON.stringify(remote.progress));
        this.setLocalSyncedAt(remoteTs);
        return { status: 'pulled', remoteTs, localTs };
      }
      if (localTs > remoteTs) {
        await this._push(App.progress);
        return { status: 'pushed-newer-local' };
      }
      return { status: 'in-sync' };
    } catch (err) {
      console.warn('[sync] start failed:', err.message);
      return { status: 'error', error: err.message };
    }
  },

  // Blocking version used by pages that rely on fresh data before rendering.
  // Returns the status object.
  async startAndWait() {
    return await this.start();
  },
};

// Auto-hook into App.saveProgress so every change triggers a debounced push.
(function hookSaveProgress() {
  if (typeof App === 'undefined' || App._syncHooked) return;
  const orig = App.saveProgress.bind(App);
  App.saveProgress = function () {
    orig();
    Sync.schedulePush();
  };
  App._syncHooked = true;
})();
