# python3 test_ghazal_marks.py
from export_divan import ghazal_marks, verses

g = """دل ناداں تجھے ہوا کیا ہے
آخر اس درد کی دوا کیا ہے

ہم ہیں مشتاق اور وہ بے زار
یا الٰہی یہ ماجرا کیا ہے

میں نے مانا کہ کچھ نہیں غالبؔ
مفت ہاتھ آئے تو برا کیا ہے"""
assert ghazal_marks(verses(g, False)[0]) == {"Maqta": 2, "Radif": "کیا ہے", "Matla": 0}

# first couplet does not rhyme (matla missing): no radif/matla, maqta still found
no_matla = g.replace("آخر اس درد کی دوا کیا ہے", "آخر اس درد کی دوا کیا ہم")
assert ghazal_marks(verses(no_matla, False)[0]) == {"Maqta": 2}
print("ok")
