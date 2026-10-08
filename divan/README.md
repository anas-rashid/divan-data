# Divan-owned content

Works edited or published in Divan, kept here so the daily Wikisource sync never overwrites them
(Divan's copy takes precedence; see the divan app, docs/content-model.md).

- `<work url>.dtx`: the work in Divan text, the readable source (one misra or paragraph per line,
  so git diffs show exactly what changed). Written by the Divan app when a moderator's change is
  published.
- `<work url>.json`: generated from the `.dtx` by the app: `Title`, `Verses` (the site's verse layout)
  and `Edited` (who and when). `export_divan.py` uses it in place of the Wikisource text.

The work url is the site path, e.g. `p266/ghazal/sh7870` for `/p266/ghazal/sh7870`.
