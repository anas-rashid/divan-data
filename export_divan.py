#!/usr/bin/env python3
"""Write divan.db in the ganjoor-data layout (manifest.json, poets/, index/) so GanjoorService's
"public data import" and any ganjoor-data client can read it unchanged.
Format: https://github.com/ganjoor/ganjoor-data/blob/main/API.md"""
import json, os, re, shutil, sqlite3, time

D = os.path.dirname(os.path.abspath(__file__))
SHARD = 2000
GENRES = {"غزل": "ghazal", "نظم": "nazm", "رباعی": "rubai", "رباعیات": "rubai", "قطعہ": "qita", "قطعات": "qita",
          "مرثیہ": "marsiya", "مثنوی": "masnavi", "قصیدہ": "qasida", "نثر": "nasr", "شاعری": "shaeri",
          "مضمون": "mazmoon", "خطوط": "khutoot", "سلام": "salam", "نعت": "naat", "حمد": "hamd"}

db = sqlite3.connect(f"{D}/divan.db")
# ids are minted once and kept forever, so URLs/ids stay stable across daily syncs
db.execute("CREATE TABLE IF NOT EXISTS divan_ids(kind TEXT, key TEXT, id INTEGER, PRIMARY KEY(kind, key))")


def gid(kind, key):
    r = db.execute("SELECT id FROM divan_ids WHERE kind=? AND key=?", (kind, key)).fetchone()
    if r:
        return r[0]
    n = (db.execute("SELECT max(id) FROM divan_ids WHERE kind=?", (kind,)).fetchone()[0] or 0) + 1
    db.execute("INSERT INTO divan_ids VALUES (?,?,?)", (kind, key, n))
    return n


def hijri(ce):
    """Approximate lunar Hijri year from a CE year (Ganjoor stores poet years in Hijri)."""
    try:
        return round((int(ce) - 622) * 33 / 32)
    except (TypeError, ValueError):
        return 0


URDU_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def ud(s):
    """Western -> Eastern Arabic (Urdu) digits for display text; ids/urls keep ASCII."""
    return s.translate(URDU_DIGITS) if isinstance(s, str) else s


def write(path, obj):
    path = os.path.join(D, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def verses(text, prose):
    """Split into Ganjoor verses: prose -> Paragraph; stanzas with even line counts -> Right/Left couplets,
    odd -> Single lines (free verse)."""
    out, couplet = [], 0
    for stanza in re.split(r"\n\s*\n", (text or "").strip()):
        lines = [l.strip() for l in stanza.splitlines() if l.strip()]
        if not lines:
            continue
        if prose:
            out.append(("Paragraph", " ".join(lines), couplet)); couplet += 1
        elif len(lines) % 2 == 0:
            for i, l in enumerate(lines):
                out.append(("Right" if i % 2 == 0 else "Left", l, couplet))
                couplet += i % 2
        else:
            for l in lines:
                out.append(("Single", l, couplet)); couplet += 1
    return [{"VOrder": i + 1, "Position": p, "Text": t, "CoupletIndex": c, "SectionIndex1": 0}
            for i, (p, t, c) in enumerate(out)], couplet


def main():
    for p in ("poets", "index"):
        shutil.rmtree(os.path.join(D, p), ignore_errors=True)
    poets = db.execute("""SELECT p.page, p.name, p.birth_year, p.death_year, coalesce(p.intro, p.description), p.image
                          FROM poets p WHERE EXISTS (SELECT 1 FROM works w WHERE w.poet_page=p.page)""").fetchall()
    manifest, cat_idx, poem_idx, poem_count = [], {}, {}, 0
    for page, name, born, died, desc, image in poets:
        pid = gid("poet", page)
        purl = f"/p{pid}"
        write(f"poets{purl}/poet.json", {
            "Id": pid, "Name": name, "Nickname": name, "Description": ud(desc), "FullUrl": purl,
            "ImageUrl": f"https://commons.wikimedia.org/wiki/Special:FilePath/{image}" if image else None,
            "BirthYearInLHijri": hijri(born), "ValidBirthDate": bool(hijri(born)),
            "DeathYearInLHijri": hijri(died), "ValidDeathDate": bool(hijri(died)),
            "BirthPlace": None, "DeathPlace": None})
        manifest.append({"Id": pid, "Nickname": name, "FullUrl": purl})

        # category tree from section paths ("شاعری > بانگ درا (1924)")
        cats = {(): {"Id": gid("cat", page), "PoetId": pid, "ParentId": None, "Title": name, "FullUrl": purl,
                     "Description": ud(desc), "DescriptionHtml": None, "BookName": None, "ChildCats": [], "Poems": []}}
        def cat(path):
            if path in cats:
                return cats[path]
            parent = cat(path[:-1])
            cid = gid("cat", page + " > " + " > ".join(path))
            slug = GENRES.get(path[-1], f"c{cid}")
            if any(c["FullUrl"] == f"{parent['FullUrl']}/{slug}" for c in parent["ChildCats"]):
                slug = f"c{cid}"
            c = {"Id": cid, "PoetId": pid, "ParentId": parent["Id"], "Title": ud(path[-1]),
                 "FullUrl": f"{parent['FullUrl']}/{slug}", "Description": None, "DescriptionHtml": None,
                 "BookName": None, "ChildCats": [], "Poems": []}
            parent["ChildCats"].append({"Id": cid, "Title": c["Title"], "FullUrl": c["FullUrl"]})
            cats[path] = c
            return c

        for title, kind, section, text, url in db.execute(
                "SELECT title, kind, section, text_ur, url FROM works WHERE poet_page=? ORDER BY title", (page,)):
            path = tuple(s.strip() for s in section.split(">")) if section else ()
            c = cat(path)
            wid = gid("poem", title)
            shown = ud(title.replace("/", " ۔ "))
            v, couplets = verses(ud(text), kind == "prose")
            fmt = "Ghazal" if any("غزل" in s for s in path) else None
            purl_ = f"{c['FullUrl']}/sh{wid}"
            full_title = " » ".join([name, *map(ud, path), shown])
            write(f"poets{purl_}.json", {
                "Id": wid, "CatId": c["Id"], "Title": shown, "FullTitle": full_title, "FullUrl": purl_,
                "RhymeLetters": None, "SourceName": "ویکی ماخذ", "SourceUrlSlug": "wikisource", "SourceUrl": url,
                "Language": "ur-PK", "PoemSummary": None, "Metre": None,
                "Sections": [{"Index": 0, "Number": 1, "SectionType": "WholePoem", "VerseType": "First",
                              "RhymeLetters": None, "PlainText": "\r\n".join(x["Text"] for x in v), "HtmlText": None,
                              "PoemFormat": fmt, "Language": "ur-PK", "CoupletsCount": couplets}],
                "Verses": v})
            c["Poems"].append({"Id": wid, "Title": shown, "FullUrl": purl_})
            poem_idx[wid] = purl_
            poem_count += 1

        for c in cats.values():
            c["ChildCats"].sort(key=lambda x: x["Id"])
            c["Poems"].sort(key=lambda x: x["Id"])
            write(f"poets{c['FullUrl']}/_cat.json", c)
            cat_idx[c["Id"]] = c["FullUrl"]

    manifest.sort(key=lambda x: x["Id"])
    write("index/poets-by-id.json", {str(p["Id"]): p["FullUrl"] for p in manifest})
    for name, idx in (("cats-by-id", cat_idx), ("poems-by-id", poem_idx)):
        shards = {}
        for i, u in sorted(idx.items()):
            shards.setdefault(i // SHARD, {})[str(i)] = u
        for b, m in shards.items():
            write(f"index/{name}/{b}.json", m)
    write("languages.json", [{"Id": 1, "Name": "اردو", "Code": "ur", "NativeName": "اردو", "RightToLeft": True}])
    write("metres.json", [])
    write("manifest.json", {
        "SchemaVersion": 1, "GeneratedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "PoetsCount": len(manifest), "PoemsCount": poem_count, "IdIndexShardSize": SHARD,
        "UrlTemplates": {"Poet": "poets/{poetSlug}/poet.json", "Category": "poets/{poetSlug}/{catPath}/_cat.json",
                         "Poem": "poets/{poetSlug}/{catPath}/{poemSlug}.json", "PoetIdIndex": "index/poets-by-id.json",
                         "CatIdIndexShard": "index/cats-by-id/{bucket}.json",
                         "PoemIdIndexShard": "index/poems-by-id/{bucket}.json"},
        "Poets": manifest})
    db.commit()
    print({"poets": len(manifest), "poems": poem_count, "cats": len(cat_idx)})


if __name__ == "__main__":
    main()
