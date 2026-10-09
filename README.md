# دیوان · Divan

A local, searchable SQLite database of **classical Urdu literature, both poetry and prose**: ghazals, nazms, marsiyas, masnavis, letters, dastans and essays by poets and writers such as Mir, Sauda, Dard, Ghalib, Momin, Zauq, Dagh, Anees, Hali, Akbar Allahabadi, Allama Iqbal, Mir Amman, Sir Syed and Nazir Ahmad. Each author entry includes a short introduction.

Everything is in **Urdu script**.

## Sources

- **Texts:** [Urdu Wikisource](https://ur.wikisource.org) (ویکی ماخذ). The works are in the public domain (`{{PD-old}}`, `{{PD-Pakistan}}`, …), and the license tag is kept on every record.
- **Author intros:** the lead section of each author's [Urdu Wikipedia](https://ur.wikipedia.org) article.

Everything is fetched through the official MediaWiki API.

## Database (`divan.db`)

| table | contents |
|---|---|
| `poets` | `page`, `name`, `years`, `birth_year`, `death_year`, `description`, `image`, `wikipedia`, `wikidata`, `intro`, `url` |
| `works` | `title`, `poet_page`, `kind` (`poetry` / `prose`), `section` (genre or book, e.g. `شاعری > بانگ درا (1924)`), `year`, `text_ur`, `license`, `url` |
| `works_fts`, `poets_fts` | SQLite FTS5 full-text indexes |

In poetry, lines are separated by `\n` and couplets or stanzas by a blank line.

## Usage

```sh
python3 wikisource.py    # first build ~30 min; later runs fetch only pages edited since the last run
python3 build_index.py   # full-text index + export/poets.jsonl, export/works.jsonl
```

Python 3.9+ standard library only. (Search needs FTS5. Python's `sqlite3` has it; Apple's built-in `sqlite3` command does not, so use Python or `brew install sqlite`.)

A Gitea Actions workflow (`.gitea/workflows/sync.yml`) runs `update.sh` daily. It commits only when the data changed.

```sql
-- Iqbal's Bang-e-Dra
SELECT title, text_ur FROM works WHERE poet_page='مصنف:محمد اقبال' AND section LIKE '%بانگ درا%';

-- all prose
SELECT poet_page, title FROM works WHERE kind='prose';

-- full-text search
SELECT title, poet_page FROM works_fts WHERE works_fts MATCH 'خودی';
```

## Site/API format (Ganjoor-compatible)

The repo root also holds the data in the [ganjoor-data](https://github.com/ganjoor/ganjoor-data) layout (`manifest.json`, `poets/`, `index/`, built by `export_divan.py`). It works as a static API over jsDelivr with no server:

    https://cdn.jsdelivr.net/gh/anas-rashid/divan-data@main/manifest.json
    https://cdn.jsdelivr.net/gh/anas-rashid/divan-data@main/poets/p238/_cat.json        # Iqbal

It also loads directly into [GanjoorService](https://github.com/ganjoor/GanjoorService) through its "public data import" page: give it the base URL above. Poets are `/p{id}`, categories are a genre slug (`ghazal`, `nazm`, …) or `c{id}`, and poems are `sh{id}`. Ids stay stable across syncs. Poet years are converted to approximate Hijri, following Ganjoor's convention.

## License

- **Data: [CC BY-SA 4.0](LICENSE).** Everything this repository publishes: `divan.db`, `manifest.json`, `poets/`, `index/`, `export/`, and `divan/` (Divan's own moderated versions, arrangements, tags and e-book records). The literary works themselves are in the public domain; the compilation comes from Urdu Wikisource, Wikipedia and Divan's moderators. When reusing it, credit *"Urdu Wikisource and Wikipedia contributors, and Divan"* and share alike. Every record keeps its source `url`.
- **Code: [MIT](LICENSE-CODE).** The scripts (`*.py`, `*.sh`) and the sync workflow.
