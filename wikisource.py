#!/usr/bin/env python3
"""Build divan.db from Urdu Wikisource (public-domain texts, CC BY-SA 4.0 site)
plus short poet intros from Urdu Wikipedia. Uses the MediaWiki API, 50 pages per request."""
import json, os, re, sqlite3, time, urllib.parse, urllib.request

WS = "https://ur.wikisource.org/w/api.php"
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "divan.db")
UA = "divan-dataset/0.1 (non-commercial Urdu poetry archive; python-urllib)"

db = sqlite3.connect(DB)
db.executescript("""
CREATE TABLE IF NOT EXISTS poets(page TEXT PRIMARY KEY, name TEXT, years TEXT, birth_year TEXT, death_year TEXT,
  description TEXT, image TEXT, wikipedia TEXT, wikidata TEXT, intro TEXT, url TEXT);
CREATE TABLE IF NOT EXISTS works(title TEXT PRIMARY KEY, poet_page TEXT, kind TEXT, section TEXT, year TEXT,
  text_ur TEXT, license TEXT, url TEXT);
CREATE INDEX IF NOT EXISTS works_poet ON works(poet_page);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS poet_aliases(alias TEXT PRIMARY KEY, canonical TEXT);
""")

if "ord" not in [r[1] for r in db.execute("PRAGMA table_info(works)")]:
    db.execute("ALTER TABLE works ADD COLUMN ord REAL")  # published order within the author's list


def api(base, **params):
    params.update(format="json", formatversion=2, maxlag=5)
    for i in range(5):
        try:
            req = urllib.request.Request(base, data=urllib.parse.urlencode(params).encode(), headers={"User-Agent": UA})  # POST: 50 Urdu titles overflow a GET URL
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            if d.get("error", {}).get("code") == "maxlag":
                raise RuntimeError("maxlag")
            return d
        except Exception:
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"API failed: {params}")


def wikitexts(titles):
    """{requested title: (resolved title, wikitext)} following redirects, 50 per request."""
    out = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        q = api(WS, action="query", prop="revisions", rvprop="content", rvslots="main",
                titles="|".join(chunk), redirects=1)["query"]
        alias = {}
        for k in ("normalized", "redirects"):
            for r in q.get(k, []):
                alias[r["from"]] = r["to"]
        pages = {p["title"]: p["revisions"][0]["slots"]["main"]["content"]
                 for p in q.get("pages", []) if "revisions" in p}
        for t in chunk:
            r = t
            while r in alias:
                r = alias[r]
            if r in pages:
                out[t] = (r, pages[r])
        time.sleep(0.5)
    return out


def tpl_field(text, name):
    m = re.search(rf"^\s*\|\s*{name}\s*=(.*)$", text, re.M)
    return m.group(1).strip() or None if m else None


def page_url(t):
    return "https://ur.wikisource.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"))


def clean(s):
    s = re.sub(r"<!--.*?-->|<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", s, flags=re.S)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''?|<[^>]+>|‏|‎", "", s)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(l.rstrip() for l in s.splitlines())).strip()


def poem_text(wt):
    poems = re.findall(r"<poem[^>]*>(.*?)</poem>", wt, re.S)
    if poems:
        return "\n\n".join(clean(p) for p in poems)
    body = re.sub(r"\{\{\s*header.*?\n\}\}", "", wt, flags=re.S | re.I)
    body = re.sub(r"\[\[(Category|زمرہ):[^\]]*\]\]", "", body)
    return clean(body)


def author_links(wt):
    """[(target, section path)] from an author page's bullet lists."""
    path, out = {}, []
    for line in wt.splitlines():
        h = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if h:
            lvl = len(h.group(1))
            path = {k: v for k, v in path.items() if k < lvl}
            path[lvl] = clean(h.group(2))
            continue
        if line.startswith("*"):
            for t in re.findall(r"\[\[([^|\]#]+)", line):
                t = t.strip()
                if ":" not in t and not t.startswith("/"):
                    out.append((t, " > ".join(v for k, v in sorted(path.items()) if v != "تصانیف")))
    return out


def all_authors():
    titles, cont = [], {}
    while True:
        d = api(WS, action="query", list="allpages", apnamespace=102, aplimit=500, **cont)
        titles += [p["title"] for p in d["query"]["allpages"]]
        if "continue" not in d:
            return titles
        cont = {"apcontinue": d["continue"]["apcontinue"]}


def intros(wp_titles):
    """Plain-text lead section from ur.wikipedia, 20 per request."""
    out = {}
    base = "https://ur.wikipedia.org/w/api.php"
    for i in range(0, len(wp_titles), 20):
        chunk = wp_titles[i:i + 20]
        q = api(base, action="query", prop="extracts", exintro=1, explaintext=1, exlimit=20,
                titles="|".join(chunk), redirects=1)["query"]
        alias = {r["from"]: r["to"] for k in ("normalized", "redirects") for r in q.get(k, [])}
        pages = {p["title"]: p for p in q.get("pages", [])}
        for t in chunk:
            r = alias.get(alias.get(t, t), alias.get(t, t))
            if r in pages:
                out[t] = pages[r]
        time.sleep(0.5)
    return out


def changed_since(ts):
    """Titles in the main namespace edited/created on Wikisource since ts (recentchanges keeps ~30 days)."""
    titles, cont = set(), {}
    while True:
        d = api(WS, action="query", list="recentchanges", rcnamespace=0, rcdir="newer", rcstart=ts,
                rcprop="title", rclimit=500, **cont)
        titles |= {c["title"] for c in d["query"]["recentchanges"]}
        if "continue" not in d:
            return titles
        cont = {"rccontinue": d["continue"]["rccontinue"]}


def merge_duplicate_poets(links, resolved):
    """Author pages linking the same Wikipedia article (after redirects, `resolved`: link -> article title)
    are one poet (e.g. two Ghalib pages): keep the page with the most listed works, map the others to it.
    Returns {alias page: canonical page}."""
    counts = {}
    for _, a, _ in links:
        counts[a] = counts.get(a, 0) + 1
    groups = {}
    for page, wp in db.execute("SELECT page, wikipedia FROM poets WHERE wikipedia IS NOT NULL"):
        groups.setdefault(resolved.get(wp, wp), []).append(page)
    alias = dict(db.execute("SELECT alias, canonical FROM poet_aliases"))
    for pages in groups.values():
        if len(pages) > 1:
            keep = max(pages, key=lambda p: (counts.get(p, 0), p))
            alias.update({p: keep for p in pages if p != keep})
    for a, c in alias.items():
        db.execute("INSERT OR REPLACE INTO poet_aliases VALUES (?,?)", (a, c))
        db.execute("UPDATE works SET poet_page=? WHERE poet_page=?", (c, a))
        db.execute("DELETE FROM poets WHERE page=?", (a,))
    db.commit()
    if alias:
        print("merged duplicate author pages:", alias)
    return alias


def main():
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    last = (db.execute("SELECT value FROM meta WHERE key='last_run'").fetchone() or [None])[0]
    authors = all_authors()
    print(len(authors), "author pages")
    apages = wikitexts(authors)
    links = []  # (work title, poet page, section)
    for a, (_, wt) in apages.items():
        f = lambda n: tpl_field(wt, n)
        wp = re.sub(r"^:?(ur:)?", "", f("wikipedia") or "") or None  # "ur:X" and ":ur:X" forms
        db.execute("INSERT OR REPLACE INTO poets(page,name,years,birth_year,death_year,description,image,wikipedia,wikidata,url) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (a, f("firstname") or a.split(":", 1)[1], f("dates"), f("birthyear"), f("deathyear"),
                    f("description"), f("image"), wp, f("wikidata"), page_url(a)))
        links += [(t, a, s) for t, s in author_links(wt)]
    db.commit()

    # Urdu Wikipedia intros
    wps = [r[0] for r in db.execute("SELECT DISTINCT wikipedia FROM poets WHERE wikipedia IS NOT NULL")]
    ur = intros(wps)
    for t, p in ur.items():
        db.execute("UPDATE poets SET intro=? WHERE wikipedia=?", (p.get("extract"), t))
    db.commit()
    print(len(ur), "intros")
    alias = merge_duplicate_poets(links, {t: p["title"] for t, p in ur.items()})
    # ord = position in the author page's list (the published order of books and poems)
    links = [(t, alias.get(a, a), s, i) for i, (t, a, s) in enumerate(links)]

    # Works; index-like pages (no <poem>, mostly links) are expanded one level
    seen = {r[0] for r in db.execute("SELECT title FROM works")}
    if last:  # incremental: refetch pages edited since the last run
        changed = changed_since(last)
        seen -= changed
        print(f"{len(changed)} pages changed since {last}", flush=True)
    queue, depth = links, 0
    while queue and depth < 3:
        todo = {}
        for t, a, s, o in queue:
            todo.setdefault(t, (a, s, o))
        # refresh order for every listed work, including already-stored ones
        db.executemany("UPDATE works SET ord=? WHERE title=?", [(o, t) for t, (_, _, o) in todo.items()])
        pending = [t for t in todo if t not in seen]
        print(f"depth {depth}: {len(pending)} pages to fetch", flush=True)
        nxt = []
        for i in range(0, len(pending), 500):  # commit + report every 500 pages
            texts = wikitexts(pending[i:i + 500])
            for t, (title, wt) in texts.items():
                a, s, o = todo[t]
                if title in seen:
                    continue
                seen.add(title)
                if "<poem" not in wt and len(re.findall(r"^\*\s*\[\[", wt, re.M)) >= 3:
                    kids = [c for c, _ in author_links(wt)] + [title + c for c in re.findall(r"\[\[(/[^|\]]+)", wt)]
                    nxt += [(c, a, f"{s} > {title}".strip(" >"), o + (j + 1) / 10000) for j, c in enumerate(kids)]
                    continue
                lic = re.findall(r"\{\{\s*(PD[^}|]*)", wt)
                db.execute("INSERT OR REPLACE INTO works(title, poet_page, kind, section, year, text_ur, license, url, ord) VALUES (?,?,?,?,?,?,?,?,?)",
                           (title, a, "poetry" if "<poem" in wt else "prose", s or None, tpl_field(wt, "year"), poem_text(wt), lic[0].strip() if lic else None, page_url(title), o))
            db.commit()
            print(f"  {min(i + 500, len(pending))}/{len(pending)}, works total {db.execute('SELECT count(*) FROM works').fetchone()[0]}", flush=True)
        queue, depth = nxt, depth + 1
    db.execute("INSERT OR REPLACE INTO meta VALUES ('last_run', ?)", (started,))
    db.commit()


if __name__ == "__main__":
    main()
