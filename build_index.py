#!/usr/bin/env python3
"""Build FTS5 full-text search over divan.db and export JSONL. Safe to re-run."""
import json, os, sqlite3

d = os.path.dirname(os.path.abspath(__file__))
db = sqlite3.connect(f"{d}/divan.db")
db.executescript("""
DROP TABLE IF EXISTS works_fts;
CREATE VIRTUAL TABLE works_fts USING fts5(title, poet_page UNINDEXED, kind UNINDEXED, section, text_ur,
  content='works', tokenize='unicode61 remove_diacritics 2');
INSERT INTO works_fts(rowid, title, poet_page, kind, section, text_ur) SELECT rowid, title, poet_page, kind, section, text_ur FROM works;
DROP TABLE IF EXISTS poets_fts;
CREATE VIRTUAL TABLE poets_fts USING fts5(page UNINDEXED, name, description, intro_ur, intro_en,
  content='poets', tokenize='unicode61 remove_diacritics 2');
INSERT INTO poets_fts(rowid, page, name, description, intro_ur, intro_en) SELECT rowid, page, name, description, intro_ur, intro_en FROM poets;
""")
db.commit()
db.execute("VACUUM")

os.makedirs(f"{d}/export", exist_ok=True)
db.row_factory = sqlite3.Row
for t in ("poets", "works"):
    with open(f"{d}/export/{t}.jsonl", "w", encoding="utf-8") as f:
        for r in db.execute(f"SELECT * FROM {t} ORDER BY 1"):
            f.write(json.dumps(dict(r), ensure_ascii=False) + "\n")
print({t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("poets", "works")})
