// Zotero Web API v3 client (runs in the browser; the key never leaves this device except to api.zotero.org).
(function (global) {
  "use strict";

  const API = "https://api.zotero.org";
  const SETTINGS_KEY = "paperfeed.zotero";
  const ADDED_KEY = "paperfeed.zotero.added";

  function safeGet(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
  }

  const defaults = { apiKey: "", libraryType: "user", libraryId: "", collectionKey: "", addNote: true, addPdfLink: true };
  const getSettings = () => ({ ...defaults, ...safeGet(SETTINGS_KEY, {}) });
  const saveSettings = (s) => safeSet(SETTINGS_KEY, s);
  const clearSettings = () => { try { localStorage.removeItem(SETTINGS_KEY); } catch {} };
  const isConfigured = (s = getSettings()) => Boolean(s.apiKey && s.libraryId);

  const addedMap = () => safeGet(ADDED_KEY, {});
  const paperKey = (p) => p.doi ? `doi:${p.doi.toLowerCase()}` : p.url;
  const isAdded = (p) => Boolean(addedMap()[paperKey(p)]);
  function markAdded(p, itemKey) { const m = addedMap(); m[paperKey(p)] = itemKey; safeSet(ADDED_KEY, m); }

  const escapeHtml = (s) => String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  /** Convert a paperfeed paper into a Zotero item JSON. */
  function toZoteroItem(p, s = getSettings()) {
    const creators = p.authors.map((a) => ({ creatorType: "author", ...global.Cite.splitName(a) }));
    const preprint = global.Cite.isPreprint(p);
    const base = {
      title: p.title,
      creators,
      abstractNote: p.abstract || "",
      date: p.published || "",
      url: p.url,
      DOI: p.doi || "",
      tags: [{ tag: "paperfeed" }, ...(p.field ? [{ tag: p.field }] : [])],
      collections: s.collectionKey ? [s.collectionKey.trim()] : [],
      extra: `paperfeed: ${p.date}`,
    };
    if (preprint) {
      const repo = p.arxiv_id ? "arXiv" : p.venue;
      return { itemType: "preprint", ...base, repository: repo, archiveID: p.arxiv_id ? `arXiv:${p.arxiv_id}` : "", libraryCatalog: repo };
    }
    return { itemType: "journalArticle", ...base, publicationTitle: p.journal };
  }

  function noteHtml(p) {
    const sec = [["要約", p.summary], ["背景", p.background], ["手法", p.method], ["結果", p.results], ["研究との関係", p.relation], ["読みどころ", p.recommend]];
    const paras = (t) => String(t || "").split(/\n\s*\n/).map((x) => `<p>${escapeHtml(x.trim())}</p>`).join("");
    return `<h1>paperfeed ${escapeHtml(p.date)}</h1>` + sec.filter(([, t]) => t).map(([h, t]) => `<h2>${h}</h2>${paras(t)}`).join("");
  }

  const writeToken = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("");

  async function post(s, items) {
    const lib = s.libraryType === "group" ? "groups" : "users";
    const res = await fetch(`${API}/${lib}/${encodeURIComponent(s.libraryId)}/items`, {
      method: "POST",
      headers: {
        "Zotero-API-Key": s.apiKey,
        "Zotero-API-Version": "3",
        "Zotero-Write-Token": writeToken(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(items),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      const hint = res.status === 403 ? "（キーに書き込み権限があるか確認してください）" : "";
      throw new Error(`Zotero ${res.status}: ${text.slice(0, 200)}${hint}`);
    }
    const data = await res.json();
    const failed = Object.values(data.failed || {});
    if (failed.length) throw new Error(`Zotero: ${failed.map((f) => f.message).join("; ")}`);
    return data;
  }

  /** Add a paper (and optional note / PDF link) to Zotero. Returns the new item key. */
  async function addPaper(p) {
    const s = getSettings();
    if (!isConfigured(s)) throw new Error("Zotero が未設定です");
    const data = await post(s, [toZoteroItem(p, s)]);
    const key = (data.successful && data.successful["0"] && data.successful["0"].key) || (data.success && data.success["0"]);
    if (!key) throw new Error("Zotero: 応答にアイテムキーがありません");
    const children = [];
    if (s.addNote) children.push({ itemType: "note", parentItem: key, note: noteHtml(p), tags: [{ tag: "paperfeed" }] });
    if (s.addPdfLink && p.pdf_url) children.push({ itemType: "attachment", linkMode: "linked_url", parentItem: key, title: "PDF", url: p.pdf_url, contentType: "application/pdf", tags: [] });
    if (children.length) {
      try { await post(s, children); } catch (e) { console.warn("child items failed", e); }
    }
    markAdded(p, key);
    return key;
  }

  /** Check a key: returns {userID, username, canWrite}. */
  async function checkKey(apiKey) {
    const res = await fetch(`${API}/keys/current`, { headers: { "Zotero-API-Key": apiKey, "Zotero-API-Version": "3" } });
    if (!res.ok) throw new Error(`キーを確認できませんでした (${res.status})`);
    const d = await res.json();
    const lib = (d.access && d.access.user) || {};
    return { userID: String(d.userID || ""), username: d.username || "", canWrite: Boolean(lib.write) };
  }

  global.Zotero = { getSettings, saveSettings, clearSettings, isConfigured, isAdded, addPaper, checkKey, toZoteroItem, noteHtml };
})(window);
