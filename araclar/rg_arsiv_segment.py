#!/usr/bin/env python3
"""Eski Resmî Gazete sayılarının arşiv PDF'lerinden (resmigazete.gov.tr/arsiv/<sayı>.pdf)
belge segmentleri üretir. Sayfa sınırları ../arastirma/arsiv/sinir*.json dosyalarındadır
(ajanlarca gazete metninden belirlenir). Çıktı: kaynak-isleme/segmentler/rg-arsiv.json
Ardından: python araclar/kitaptan_cikar.py --kaynak-dizin kaynak-isleme/indirilen kaynak-isleme/segmentler/rg-arsiv.json
"""
import json, sys
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import belgeleri_oku  # noqa: E402
ARS = KOK.parent / "arastirma" / "arsiv"


def main():
    liste = {x["id"]: x for x in json.loads((ARS / "liste.json").read_text(encoding="utf-8"))}
    belgeler = belgeleri_oku()
    tum = {}
    for b in belgeler.values():
        tum[b["id"]] = b
        for _, eski in b.get("eski_kimlikler", []):
            tum.setdefault(eski, b)
    segmentler = []
    for f in sorted(ARS.glob("sinir*.json")):
        for i, s in json.loads(f.read_text(encoding="utf-8")).items():
            if s.get("bulunamadi") or i not in liste or not s.get("baslangic"):
                continue
            b = tum.get(i)
            if not b or b["tam_metin"]:
                continue
            x = liste[i]
            veri = {k: b.get(k) for k in ("id", "baslik", "tur", "tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu", "etiketler", "not", "durum")}
            veri.update(kaynak="Resmî Gazete arşivi (ilk yayımlanan metin; sonraki değişiklikler işlenmemiş olabilir)",
                        kaynak_url=f"https://www.resmigazete.gov.tr/arsiv/{x['rg_sayi']}.pdf", kaynak_pdf=x["pdf"],
                        pdf_baslangic=int(s["baslangic"]), pdf_bitis=int(s.get("bitis") or s["baslangic"]), ocr=True)
            if s.get("baslik_satiri"):
                veri["baslik_satiri"] = s["baslik_satiri"]
            if s.get("sonraki_baslik_satiri"):
                veri["sonraki_baslik_satiri"] = s["sonraki_baslik_satiri"]
            segmentler.append({k: v for k, v in veri.items() if v not in (None, "", [])})
    (KOK / "kaynak-isleme" / "segmentler" / "rg-arsiv.json").write_text(
        json.dumps(segmentler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(segmentler), "arşiv segmenti")


if __name__ == "__main__":
    main()
