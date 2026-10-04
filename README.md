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

## License

- **Code:** [MIT](LICENSE).
- **Data** (`divan.db`, `export/`): the literary works are in the public domain. The compilation is derived from Wikisource and Wikipedia and is shared under **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**. When reusing it, credit *"Urdu Wikisource and Wikipedia contributors"* and share alike. Every record keeps its source `url`.

Corrections belong upstream: fix the text on Wikisource and re-run the script.
