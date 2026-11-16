(function () {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const state = { days: [], day: null, papers: [], field: "" };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const paras = (t) => String(t || "").split(/\n\s*\n/).map((x) => x.trim()).filter(Boolean).map((x) => `<p>${esc(x)}</p>`).join("");

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), 2600);
  }

  async function getJSON(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`${url}: ${res.status}`);
    return res.json();
  }

  function formatDay(d) {
    const dt = new Date(d + "T00:00:00");
    if (isNaN(dt)) return d;
    const w = "日月火水木金土"[dt.getDay()];
    return `${d.replaceAll("-", ".")}（${w}）`;
  }

  // ---- data ----------------------------------------------------------------
  async function init() {
    bindSettings();
    try {
      const idx = await getJSON("data/index.json");
      state.days = idx.days || [];
    } catch {
      state.days = [];
    }
    if (!state.days.length) {
      $("#status").textContent = "まだ論文がありません。GitHub Actions の初回実行を待つか、手動で実行してください。";
      $("#day-select").disabled = true;
      $("#prev-day").disabled = $("#next-day").disabled = true;
      return;
    }
    const sel = $("#day-select");
    sel.innerHTML = state.days.map((d) => `<option value="${esc(d.date)}">${esc(formatDay(d.date))}　${d.count}本</option>`).join("");
    sel.addEventListener("change", () => go(sel.value));
    $("#prev-day").addEventListener("click", () => step(1));
    $("#next-day").addEventListener("click", () => step(-1));
    window.addEventListener("hashchange", () => loadDay(fromHash()));
    loadDay(fromHash());
  }

  function fromHash() {
    const h = decodeURIComponent(location.hash.slice(1));
    return state.days.some((d) => d.date === h) ? h : state.days[0].date;
  }
  function go(day) { location.hash = day; }
  function step(delta) {
    const i = state.days.findIndex((d) => d.date === state.day);
    const j = i + delta;
    if (j >= 0 && j < state.days.length) go(state.days[j].date);
  }

  async function loadDay(day) {
    state.day = day;
    const i = state.days.findIndex((d) => d.date === day);
    $("#day-select").value = day;
    $("#prev-day").disabled = i >= state.days.length - 1;
    $("#next-day").disabled = i <= 0;
    $("#status").textContent = "読み込み中…";
    $("#status").hidden = false;
    $("#papers").innerHTML = "";
    try {
      const data = await getJSON(`data/${day}.json`);
      state.papers = (data.papers || []).sort((a, b) => a.order - b.order);
    } catch (e) {
      $("#status").textContent = "読み込めませんでした。";
      return;
    }
    if (state.field && !state.papers.some((p) => p.field === state.field)) state.field = "";
    renderFilters();
    render();
  }

  // ---- rendering -----------------------------------------------------------
  function renderFilters() {
    const fields = [...new Set(state.papers.map((p) => p.field).filter(Boolean))];
    const box = $("#filters");
    if (fields.length < 2) { box.innerHTML = ""; box.hidden = true; return; }
    box.hidden = false;
    const chip = (val, label) => `<button type="button" class="chip" data-field="${esc(val)}" aria-pressed="${state.field === val}">${esc(label)}</button>`;
    box.innerHTML = chip("", "すべて") + fields.map((f) => chip(f, f)).join("");
    box.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      state.field = b.dataset.field;
      renderFilters();
      render();
    }));
  }

  const SECTIONS = [["background", "背景"], ["method", "手法"], ["results", "結果"], ["relation", "研究との関係"], ["recommend", "読みどころ"]];

  function paperHTML(p, idx) {
    const authors = p.authors.length > 8 ? p.authors.slice(0, 8).join(", ") + ` ほか${p.authors.length - 8}名` : p.authors.join(", ");
    const kindCls = p.kind === "新着" ? "tag new" : "tag";
    const zAdded = window.Zotero.isAdded(p);
    return `
<article class="paper" id="p-${esc(p.id)}">
  <div class="meta-top">
    <span class="${kindCls}">${esc(p.kind)}</span>
    <span>${esc(p.field)}</span>
    <span>${esc(p.venue)}</span>
    <span>${esc(p.published)}</span>
  </div>
  <h2><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a></h2>
  <p class="byline">${esc(authors)}</p>
  <p class="byline">${esc(p.journal)}${p.doi ? ` · doi:${esc(p.doi)}` : ""}</p>
  ${p.reason ? `<p class="reason">${esc(p.reason)}</p>` : ""}
  <div class="summary">${paras(p.summary)}</div>
  <details class="more">
    <summary>詳しく読む</summary>
    ${SECTIONS.filter(([k]) => p[k]).map(([k, h]) => `<div class="section"><h3>${h}</h3>${paras(p[k])}</div>`).join("")}
  </details>
  ${p.note ? `<p class="note">※ ${esc(p.note)}</p>` : ""}
  <div class="actions-row">
    <button type="button" class="btn ${zAdded ? "done" : ""}" data-act="zotero" data-i="${idx}">${zAdded ? "Zotero に追加済み" : "Zotero に追加"}</button>
    <button type="button" class="btn" data-act="bibtex" data-i="${idx}">BibTeX</button>
    <button type="button" class="btn" data-act="ris" data-i="${idx}">RIS</button>
    ${p.pdf_url ? `<a class="btn" href="${esc(p.pdf_url)}" target="_blank" rel="noopener">PDF</a>` : ""}
  </div>
</article>`;
  }

  function render() {
    const list = state.papers.filter((p) => !state.field || p.field === state.field);
    $("#status").hidden = list.length > 0;
    if (!list.length) $("#status").textContent = "この日の論文はありません。";
    $("#papers").innerHTML = list.map((p) => paperHTML(p, state.papers.indexOf(p))).join("");
    $("#foot-count").textContent = `${list.length} 本`;
    $("#papers").querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", onAction));
    typeset();
  }

  function typeset() {
    const run = () => window.MathJax.typesetPromise([$("#papers")]).catch((e) => console.warn(e));
    if (window.MathJax && window.MathJax.typesetPromise) run();
    else window.addEventListener("load", () => window.MathJax && window.MathJax.typesetPromise && run(), { once: true });
  }

  // ---- actions -------------------------------------------------------------
  async function onAction(ev) {
    const btn = ev.currentTarget;
    const p = state.papers[Number(btn.dataset.i)];
    const act = btn.dataset.act;
    if (act === "bibtex") {
      const text = window.Cite.toBibTeX(p);
      try { await navigator.clipboard.writeText(text); toast("BibTeX をコピーしました"); }
      catch { download(`${window.Cite.citeKey(p)}.bib`, text, "application/x-bibtex"); }
    } else if (act === "ris") {
      download(`${window.Cite.citeKey(p)}.ris`, window.Cite.toRIS(p), "application/x-research-info-systems");
    } else if (act === "zotero") {
      if (!window.Zotero.isConfigured()) { toast("先に Zotero の API キーを設定してください"); openSettings(); return; }
      if (window.Zotero.isAdded(p) && !confirm("この論文は追加済みです。もう一度追加しますか？")) return;
      btn.disabled = true;
      btn.textContent = "追加中…";
      try {
        await window.Zotero.addPaper(p);
        btn.textContent = "Zotero に追加済み";
        btn.classList.add("done");
        toast("Zotero に追加しました");
      } catch (e) {
        btn.textContent = "Zotero に追加";
        toast(e.message || String(e));
      } finally {
        btn.disabled = false;
      }
    }
  }

  function download(name, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ---- settings dialog -----------------------------------------------------
  function openSettings() {
    const f = $("#settings-form");
    const s = window.Zotero.getSettings();
    f.apiKey.value = s.apiKey;
    f.libraryType.value = s.libraryType;
    f.libraryId.value = s.libraryId;
    f.collectionKey.value = s.collectionKey;
    f.addNote.checked = s.addNote;
    f.addPdfLink.checked = s.addPdfLink;
    $("#key-status").textContent = s.apiKey ? "保存済みのキーがあります。" : "";
    $("#settings").showModal();
  }

  function bindSettings() {
    const dlg = $("#settings");
    const f = $("#settings-form");
    $("#open-settings").addEventListener("click", openSettings);
    $("#check-key").addEventListener("click", async () => {
      const st = $("#key-status");
      if (!f.apiKey.value.trim()) { st.textContent = "API キーを入力してください。"; return; }
      st.textContent = "確認中…";
      try {
        const r = await window.Zotero.checkKey(f.apiKey.value.trim());
        if (f.libraryType.value === "user") f.libraryId.value = r.userID;
        st.textContent = `ユーザー ${r.username}（ID ${r.userID}）。個人ライブラリへの書き込み: ${r.canWrite ? "可" : "不可"}`;
      } catch (e) {
        st.textContent = e.message;
      }
    });
    $("#clear-settings").addEventListener("click", () => {
      window.Zotero.clearSettings();
      f.reset();
      $("#key-status").textContent = "消去しました。";
    });
    dlg.addEventListener("close", () => {
      if (dlg.returnValue !== "save") return;
      window.Zotero.saveSettings({
        apiKey: f.apiKey.value.trim(),
        libraryType: f.libraryType.value,
        libraryId: f.libraryId.value.trim(),
        collectionKey: f.collectionKey.value.trim(),
        addNote: f.addNote.checked,
        addPdfLink: f.addPdfLink.checked,
      });
      toast("保存しました");
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
