#!/usr/bin/env python3
"""Ajan düzeltmesini denetler: calisma/surum-is/<kimlik>/duzeltme.json içindeki her maddenin son metni güncel metinle aynı mı?
Kullanım: python3 araclar/surum_kontrol.py <kimlik>"""
import json, sys, difflib, re
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
import surum_olustur as so  # noqa: E402


def kontrol_metinleri(md):
    # Bazı kaynaklarda madde ayıracı Unicode eksi, dipnot çizgisi italiktir.
    md = re.sub(r"(?m)^((?:\*\*)?(?:(?:GEÇİCİ|EK) )?MADDE\s+\d+\s*)−", r"\1–", md, flags=re.I)
    md = re.sub(r"(?m)^[ \t]*<i>[ \t]*(_{3,}|-{3,})[ \t]*</i>[ \t]*$", r"\1", md)
    return so.madde_metinleri(so.Belge(md))


def denetle(kimlik):
    d = KOK / "calisma" / "surum-is" / kimlik
    gorev = json.loads((d / "gorev.json").read_text())
    duz = json.loads((d / "duzeltme.json").read_text())
    guncel = kontrol_metinleri((d / "guncel.md").read_text())
    tarihler = [p.name.split("-ilk-")[1][:10] for p in d.glob("0-ilk-*.md")] + gorev["tarihler"]
    sorun = []
    for k in gorev["dogrulanamayan_maddeler"]:
        s = duz.get("maddeler", {}).get(k)
        if not s:
            sorun.append(f"{k}: düzeltme yok")
            continue
        if any(x.get("t") not in tarihler for x in s):
            sorun.append(f"{k}: tarihler {tarihler} dışında")
        son = kontrol_metinleri(s[-1]["md"]).get(k, "")
        oran = difflib.SequenceMatcher(None, son, guncel.get(k, ""), autojunk=False).ratio()
        if oran < 0.97:
            sorun.append(f"{k}: son metin güncel metinle uyuşmuyor (benzerlik {oran:.2f})")
    print("TAMAM" if not sorun else "\n".join(sorun))
    return not sorun


if __name__ == "__main__":
    sys.exit(0 if all(denetle(k) for k in sys.argv[1:]) else 1)

