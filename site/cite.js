// Citation helpers: name splitting, BibTeX and RIS export. Pure functions.
(function (global) {
  "use strict";

  /** "Taro Tanaka" -> {firstName:"Taro", lastName:"Tanaka"}; "Tanaka, T." -> {lastName:"Tanaka", firstName:"T."} */
  function splitName(name) {
    name = (name || "").trim();
    if (!name) return { firstName: "", lastName: "" };
    if (name.includes(",")) {
      const [last, ...rest] = name.split(",");
      return { lastName: last.trim(), firstName: rest.join(",").trim() };
    }
    const parts = name.split(/\s+/);
    if (parts.length === 1) return { firstName: "", lastName: parts[0] };
    // keep particles ("van der", "de") with the last name
    let i = parts.length - 1;
    while (i > 1 && /^(van|von|der|den|de|del|da|di|le|la|du)$/i.test(parts[i - 1])) i--;
    return { firstName: parts.slice(0, i).join(" "), lastName: parts.slice(i).join(" ") };
  }

  const isPreprint = (p) => !p.journal || p.journal.startsWith("未掲載");
  const year = (p) => (p.published || "").slice(0, 4);

  function citeKey(p) {
    const last = splitName(p.authors[0] || "anon").lastName.toLowerCase().replace(/[^a-z0-9]/g, "") || "anon";
    const word = (p.title.toLowerCase().match(/[a-z]{4,}/) || ["paper"])[0];
    return `${last}${year(p)}${word}`;
  }

  const bibEscape = (s) => String(s || "").replace(/([{}])/g, "\\$1");

  function toBibTeX(p) {
    const fields = [
      ["title", `{${bibEscape(p.title)}}`],
      ["author", p.authors.map((a) => { const n = splitName(a); return n.firstName ? `${n.lastName}, ${n.firstName}` : n.lastName; }).join(" and ")],
      ["year", year(p)],
    ];
    let type = "article";
    if (isPreprint(p)) {
      type = "misc";
      if (p.arxiv_id) {
        fields.push(["eprint", p.arxiv_id], ["archivePrefix", "arXiv"]);
        const cat = (p.venue.match(/\[(.+)\]/) || [])[1];
        if (cat) fields.push(["primaryClass", cat]);
      } else {
        fields.push(["howpublished", p.venue]);
      }
    } else {
      fields.push(["journal", p.journal]);
    }
    if (p.doi) fields.push(["doi", p.doi]);
    fields.push(["url", p.url]);
    const body = fields.filter(([, v]) => v).map(([k, v]) => `  ${k} = {${v}}`).join(",\n");
    return `@${type}{${citeKey(p)},\n${body}\n}\n`;
  }

  function toRIS(p) {
    const lines = [["TY", isPreprint(p) ? "UNPB" : "JOUR"], ["TI", p.title]];
    p.authors.forEach((a) => { const n = splitName(a); lines.push(["AU", n.firstName ? `${n.lastName}, ${n.firstName}` : n.lastName]); });
    if (p.published) lines.push(["PY", year(p)], ["DA", p.published.replaceAll("-", "/")]);
    if (!isPreprint(p)) lines.push(["JO", p.journal]);
    else lines.push(["PB", p.venue]);
    if (p.doi) lines.push(["DO", p.doi]);
    lines.push(["UR", p.url]);
    if (p.abstract) lines.push(["AB", p.abstract]);
    lines.push(["KW", "paperfeed"], ["KW", p.field], ["ER", ""]);
    return lines.map(([k, v]) => `${k}  - ${v}`).join("\r\n") + "\r\n";
  }

  global.Cite = { splitName, toBibTeX, toRIS, isPreprint, citeKey };
})(window);
