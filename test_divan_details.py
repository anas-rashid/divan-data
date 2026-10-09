# python3 test_divan_details.py
import os, tempfile
import export_divan

with tempfile.TemporaryDirectory() as d:
    export_divan.DIVAN_DIR = d
    assert export_divan.owned_details("/p1", "poet") is None
    with open(os.path.join(d, "p1.poet"), "w", encoding="utf-8") as f:
        f.write("نام: محمد اقبال\nتخلص: اقبال\nپیدائش: 1877\nوفات: \nتعارف:\nپہلا: پیراگراف\n\nدوسرا\n")
    p = export_divan.owned_details("/p1", "poet")
    assert p == {"نام": "محمد اقبال", "تخلص": "اقبال", "پیدائش": "1877", "وفات": "", "تعارف": "پہلا: پیراگراف\n\nدوسرا"}, p
    os.makedirs(os.path.join(d, "p1"))
    with open(os.path.join(d, "p1", "ghazal.book"), "w", encoding="utf-8") as f:
        f.write("عنوان: غزلیات\n")
    assert export_divan.owned_details("/p1/ghazal", "book") == {"عنوان": "غزلیات"}
print("ok")
