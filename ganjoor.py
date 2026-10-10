"""Persian (فارسی) works from Ganjoor for poets who are in both Divan and Ganjoor (ganjoor.json).

ganjoor/ganjoor-data is checked out sparsely, only the listed poets, at the pinned commit, in .ganjoor/ (not in git).
export_divan.py then adds a «فارسی» section under each such poet with Ganjoor's books and poems: verses, titles,
metre and a link to the poem on ganjoor.net. Ganjoor's AI-written summaries (PoemSummary, CoupletSummary) are left
out: Divan's content is written and reviewed by people."""
import json, os, subprocess

D = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(D, "ganjoor.json"), encoding="utf-8"))
REPO = os.path.join(D, ".ganjoor")
URL = "https://github.com/ganjoor/ganjoor-data.git"
SITE = "https://ganjoor.net"


def checkout():
    """the pinned commit, with only the listed poets' folders (a few MB instead of 500)"""
    git = lambda *a: subprocess.run(["git", "-C", REPO, *a], check=True, capture_output=True)
    if not os.path.isdir(os.path.join(REPO, ".git")):
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", "--sparse", URL, REPO], check=True)
    git("sparse-checkout", "set", *[f"poets/{p['ganjoor']}" for p in CFG["poets"]])
    have = subprocess.run(["git", "-C", REPO, "cat-file", "-e", CFG["commit"]], capture_output=True).returncode == 0
    if not have:
        git("fetch", "-q", "--filter=blob:none", "origin", CFG["commit"])
    git("checkout", "-q", "--detach", CFG["commit"])


def by_divan_page():
    return {p["divan"]: p["ganjoor"] for p in CFG["poets"]}


def read(path):
    with open(os.path.join(REPO, "poets", path.lstrip("/")), encoding="utf-8") as f:
        return json.load(f)


def poem(g, cat_id, pid, url, full_title):
    """a Ganjoor poem as a Divan poem: same layout, without the AI summaries"""
    verses = [{k: v[k] for k in ("VOrder", "Position", "Text", "CoupletIndex") if k in v} for v in g.get("Verses") or []]
    return {
        "Id": pid, "CatId": cat_id, "Title": g["Title"], "FullTitle": full_title, "FullUrl": url,
        "RhymeLetters": None, "SourceName": "گنجور", "SourceUrlSlug": "ganjoor", "SourceUrl": SITE + g["FullUrl"],
        "Language": "fa-IR", "PoemSummary": None, "Metre": g.get("Metre"),
        "Sections": [{"Index": 0, "Number": 1, "SectionType": "WholePoem", "VerseType": "First", "RhymeLetters": None,
                      "PlainText": "\r\n".join(v["Text"] for v in verses), "HtmlText": None,
                      "PoemFormat": (g.get("Sections") or [{}])[0].get("PoemFormat"), "Language": "fa-IR",
                      "CoupletsCount": len({v.get("CoupletIndex") for v in verses})}],
        "Verses": verses,
    }
