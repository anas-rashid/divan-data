# python3 test_divan_order.py
import os, tempfile
import export_divan

with tempfile.TemporaryDirectory() as d:
    export_divan.DIVAN_DIR = d
    os.makedirs(os.path.join(d, "p1"))
    c = {"FullUrl": "/p1/ghazal", "ChildCats": [],
         "Poems": [{"FullUrl": f"/p1/ghazal/sh{i}"} for i in (1, 2, 3, 4)]}
    export_divan.owned_order(c)  # no order file: unchanged
    assert [p["FullUrl"][-3:] for p in c["Poems"]] == ["sh1", "sh2", "sh3", "sh4"]
    with open(os.path.join(d, "p1", "ghazal.order"), "w", encoding="utf-8") as f:
        f.write("sh3 تیسری\nsh1 پہلی\n\nsh2 دوسری\n")  # sh4 (new since) is not listed
    export_divan.owned_order(c)
    assert [p["FullUrl"][-3:] for p in c["Poems"]] == ["sh3", "sh1", "sh2", "sh4"]
print("ok")
