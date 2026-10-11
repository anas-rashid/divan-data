# python3 test_divan_owned_new.py
import json, os, tempfile
import export_divan

written = {}
export_divan.write = lambda path, obj: written.__setitem__(path, obj)
with tempfile.TemporaryDirectory() as d:
    export_divan.DIVAN_DIR = d
    os.makedirs(os.path.join(d, "p1", "c1"))
    for slug, title in (("sh5", "موجود"), ("dibacha", "دیباچہ")):  # sh5 overrides a listed work; dibacha is new
        with open(os.path.join(d, "p1", "c1", slug + ".json"), "w", encoding="utf-8") as f:
            json.dump({"Title": title, "Verses": [{"Position": "Paragraph", "Text": "متن", "CoupletIndex": 0}], "Language": "fa-IR"}, f)
    c = {"Id": 1, "Title": "کتاب", "FullUrl": "/p1/c1", "Poems": [{"FullUrl": "/p1/c1/sh5"}]}
    first, idx = {}, {}
    assert export_divan.add_owned(c, "شاعر", first, idx) == 1
    assert [p["FullUrl"] for p in c["Poems"]] == ["/p1/c1/sh5", "/p1/c1/dibacha"]
    w = written["poets/p1/c1/dibacha.json"]
    assert w["Title"] == "دیباچہ" and w["Language"] == "fa-IR" and w["DivanOwned"] and list(idx.values()) == ["/p1/c1/dibacha"]
print("ok")
