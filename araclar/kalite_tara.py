#!/usr/bin/env python3
"""Metin kalitesi taraması: OCR hatası belirtileri, okunamayan yerler ve künye eksikleri.

Kullanım: python araclar/kalite_tara.py [--json cikti.json]
Puan = (3×[?] + 2×tipik okuma hatası + 5×bozuk karakter) × 1000 / sözcük sayısı
"""
import collections, json, re, sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HATA = re.compile(r"\b(lle|nei|olarsk|içln|bllg|ıle|Için|Ilgili|Iş|hlz|tarlh|sayıh|bır|ıçin|Yönetmel[ıl]k)\b"
                  r"|\b[a-zçğıöşü]+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\b|\w[ỈỎÕỦẢẾắằ]\w")


def tara():
    sonuc = []
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        _, bas, govde = md.read_text(encoding="utf-8").split("---\n", 2)
        v = dict(re.findall(r'^(\w+): "?(.*?)"?$', bas, re.M))
        g = re.sub(r"https?://\S+", "", govde)
        n = len(g.split())
        soru, hata, bozuk = g.count("[?]"), len(HATA.findall(g)), len(re.findall(r"[\ufffd□■]|\(cid:", g))
        puan = round((soru * 3 + hata * 2 + bozuk * 5) * 1000 / n, 1) if n >= 80 else 0
        u = v.get("kaynak_url", "")
        tip = ("pdf" if u.lower().split("?")[0].endswith(".pdf") else "kitap" if v.get("kaynak_pdf_sayfa") else
               "mevzuat.gov" if "mevzuat.gov.tr" in u else "rg" if "resmigazete" in u else "saglik.gov" if "saglik.gov.tr" in u else "yok")
        sonuc.append({"dosya": f"{md.parent.name}/{md.name}", "puan": puan, "soru": soru, "hata": hata, "sozcuk": n, "tip": tip,
                      "url": u, "kaynak": v.get("kaynak", ""), "sayfa": v.get("kaynak_pdf_sayfa", ""), "tur": v.get("tur"),
                      "tarih": v.get("tarih", ""), "rg_tarih": v.get("rg_tarih", ""), "sayi": v.get("sayi", ""), "ocr": v.get("ocr") == "true"})
    return sorted(sonuc, key=lambda s: -s["puan"])


def main():
    s = tara()
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    kotu = [x for x in s if x["puan"] >= 15]
    print(f"{len(s)} belge; puanı 15 ve üstü: {len(kotu)}; [?] içeren: {sum(1 for x in s if x['soru'])} belge, {sum(x['soru'] for x in s)} yer")
    print("kaynak türüne göre:", dict(collections.Counter(x["tip"] for x in kotu)))
    for x in kotu[:40]:
        print(f"{x['puan']:7} {x['tip']:11} {x['sozcuk']:6} {x['dosya'][:90]}")


if __name__ == "__main__":
    main()
