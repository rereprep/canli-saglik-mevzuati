#!/usr/bin/env python3
"""Ajan düzeltmelerinden (calisma/surum-is/<kimlik>/duzeltme.json) yalnız denetimi geçen maddeleri
kaynak-isleme/surum/duzeltme/<kimlik>.json olarak alır. Denetim: son metin güncel metinle ≥%97 benzer, tarihler geçerli."""
import difflib, json, sys
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
import surum_olustur as so  # noqa: E402


def main():
    hedef = KOK / "kaynak-isleme" / "surum" / "duzeltme"
    hedef.mkdir(parents=True, exist_ok=True)
    top = [0, 0]
    for d in sorted((KOK / "calisma" / "surum-is").iterdir()):
        f = d / "duzeltme.json"
        if not f.exists():
            continue
        try:
            duz = json.loads(f.read_text())
        except json.JSONDecodeError:
            print("bozuk", d.name)
            continue
        gorev = json.loads((d / "gorev.json").read_text())
        tarihler = {p.name.split("-ilk-")[1][:10] for p in d.glob("0-ilk-*.md")} | set(gorev["tarihler"])
        guncel = so.madde_metinleri(so.Belge((d / "guncel.md").read_text()))
        al = {}
        for k, kay in (duz.get("maddeler") or {}).items():
            top[1] += 1
            if not kay or any(x.get("t") not in tarihler for x in kay) or k not in guncel:
                continue
            son = so.madde_metinleri(so.Belge(kay[-1]["md"])).get(k, "")
            if difflib.SequenceMatcher(None, son, guncel[k], autojunk=False).ratio() >= 0.97:
                al[k] = sorted(kay, key=lambda x: x["t"])
        if al:
            (hedef / f"{d.name}.json").write_text(json.dumps({"maddeler": al, "notlar": duz.get("notlar", "")}, ensure_ascii=False, indent=0))
        top[0] += len(al)
        print(f"{len(al)}/{len(duz.get('maddeler') or {})} {d.name[:60]}")
    print("TOPLAM", top)


if __name__ == "__main__":
    main()

