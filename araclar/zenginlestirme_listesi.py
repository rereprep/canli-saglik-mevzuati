#!/usr/bin/env python3
"""Künye bilgisi eksik belgeler için ajan iş listesi üretir.

Her parça dosyası, belge kimliği, mevcut künye ve metnin ilk kısmını içerir.
Gemini ajanları bu listeyi okuyup kaynak-isleme/zenginlestirme/<parça>.json yazar.
Kullanım: python araclar/zenginlestirme_listesi.py --parca 4 --cikti /tmp/zengin
"""
import argparse, json, re
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parca", type=int, default=4)
    ap.add_argument("--cikti", default="/tmp/zengin")
    a = ap.parse_args()
    import sys
    sys.path.insert(0, str(KOK / "araclar"))
    from site_uret import on_bilgi_ayir
    mevcut = set()
    for js in (KOK / "kaynak-isleme" / "zenginlestirme").glob("*.json"):
        mevcut |= set(json.loads(js.read_text(encoding="utf-8")))
    isler = []
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        veri, govde = on_bilgi_ayir(md.read_text(encoding="utf-8"))
        if veri["id"] in mevcut:
            continue
        eksik = [k for k in ("tarih", "sayi", "konu") if not veri.get(k)] or (["baslik"] if veri.get("not", "").startswith("Başlık") else [])
        if veri.get("konu", "").endswith("düzenler.") and "uyarınca" in veri.get("konu", ""):
            eksik.append("konu")
        if not eksik:
            continue
        bas = re.sub(r"<[^>]+>", "", govde)[:1800]
        isler.append({"id": veri["id"], "tur": veri["tur"], "baslik": veri["baslik"], "birim": veri.get("birim", ""),
                      "tarih": veri.get("tarih", ""), "sayi": veri.get("sayi", ""), "eksik": sorted(set(eksik)), "metin_basi": bas})
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    boy = -(-len(isler) // a.parca)
    for i in range(a.parca):
        parca = isler[i * boy:(i + 1) * boy]
        Path(a.cikti, f"parca-{i + 1}.json").write_text(json.dumps(parca, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"parca-{i + 1}.json: {len(parca)} belge")


if __name__ == "__main__":
    main()

