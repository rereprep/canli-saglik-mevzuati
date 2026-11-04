#!/usr/bin/env python3
"""Cemil Özcan, Halk Sağlığı (2. baskı) kitabının eklerindeki mevzuat listelerini kataloğa aktarır.

Ekler: I sağlık kanunları ve CBK, II sağlık tüzükleri, III sağlıkla ilgili kanun/KHK,
IV sağlıkla ilgili tüzükler, V yönetmelikler, VI uygulama olanağı kalmamış yönetmelikler,
VII sağlık yönergeleri. Kalın yazılan yönetmelikler Bakanlar Kurulu / Cumhurbaşkanlığı
kararıyla yürürlüğe konulmuştur; bu bilgi "not" alanına yazılır.

Kullanım: python araclar/ozcan_ekleri.py --kitap "<Halk Sağlığı Cemil Özcan.docx>"
"""
import argparse, json, re, unicodedata
from pathlib import Path

import docx

KOK = Path(__file__).resolve().parent.parent
KAYNAK = "Özcan C. Halk Sağlığı, 2. baskı"
EKLER = [  # (başlık parçası, tür, ek adı, sağlık mevzuatı mı)
    ("SAĞLIK KANUNLARI VE CUMHURBAŞKANLIĞI", "kanun", "Ek I", True, "Sağlık kanunları ve Cumhurbaşkanlığı kararnameleri"),
    ("SAĞLIK TÜZÜKLERİ", "tuzuk", "Ek II", True, "Sağlık tüzükleri"),
    ("SAĞLIKLA İLGİLİ KANUNLAR", "kanun", "Ek III", False, "Sağlıkla ilgili kanunlar ve kanun hükmünde kararnameler"),
    ("SAĞLIKLA İLGİLİ TÜZÜKLER", "tuzuk", "Ek IV", False, "Sağlıkla ilgili tüzükler"),
    ("SAĞLIK VE SAĞLIKLA İLGİLİ YÖNETMELİKLER", "yonetmelik", "Ek V", True, "Sağlık ve sağlıkla ilgili yönetmelikler"),
    ("UYGULAMA OLANAĞI KALMAMIŞ", "yonetmelik", "Ek VI", True, "Uygulama olanağı kalmamış yönetmelikler"),
    ("SAĞLIK YÖNERGELERİ", "yonerge", "Ek VII", True, "Sağlık yönergeleri"),
]


def sade(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ı", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def iso(t):
    t = t.strip()
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", t)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return ""


def sirali_ogeler(belge):
    pi = ti = 0
    for el in belge.element.body.iterchildren():
        etiket = el.tag.split("}")[1]
        if etiket == "p":
            yield "p", belge.paragraphs[pi]
            pi += 1
        elif etiket == "tbl":
            yield "t", belge.tables[ti]
            ti += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kitap", required=True)
    a = ap.parse_args()
    belge = docx.Document(a.kitap)
    kayitlar, ek, ekler_basladi = [], None, False
    for tip, oge in sirali_ogeler(belge):
        if tip == "p":
            metin = " ".join(oge.text.split())
            if metin == "EKLER":
                ekler_basladi = True
            if ekler_basladi:
                for parca, tur, ad, saglik, ek_adi in EKLER:
                    if parca in metin.upper():
                        ek = (tur, ad, saglik, ek_adi)
                if metin == "KAYNAKLAR":
                    ek = None
            continue
        if not ek or len(oge.rows) < 2:
            continue  # başlık tabloları
        tur, ad, saglik, ek_baslik = ek
        for satir in oge.rows:
            hucreler = []
            for c in satir.cells:
                if not hucreler or c._tc is not hucreler[-1][0]:
                    hucreler.append((c._tc, " ".join(c.text.split())))
            h = [x[1] for x in hucreler]
            kalin = any(r.bold for c in satir.cells for p in c.paragraphs for r in p.runs if r.text.strip())
            if len(h) == 4:
                no, baslik, tarih, rg = h
            elif len(h) == 3:
                no, (baslik, tarih, rg) = "", h
            else:
                continue
            if not baslik:
                continue
            k = {"tur": tur, "baslik": baslik}
            if no and tur == "kanun":
                if baslik == "Cumhurbaşkanlığı Kararnamesi":
                    k.update(tur="cbk", baslik=f"{no} Sayılı Cumhurbaşkanlığı Kararnamesi")
                elif "Kanun Hükmünde Kararname" in baslik:
                    k["tur"] = "khk"
                k["sayi"] = no
            if tur in ("kanun", "tuzuk", "yonetmelik"):
                k["rg_tarih"], k["rg_sayi"] = iso(tarih), rg
                if not k["rg_tarih"] and re.fullmatch(r"\d{4}", tarih):
                    k["not"] = f"Resmî Gazete yılı: {tarih}"
            else:
                k["tarih"], k["sayi"] = iso(tarih), rg
            notlar = [k.get("not", ""), f"{ad}: {ek_baslik}."]
            if ad == "Ek VI":
                k["durum"] = "uygulama olanağı kalmamış"
            if kalin and tur == "yonetmelik":
                notlar.append("Bakanlar Kurulu / Cumhurbaşkanlığı kararıyla yürürlüğe konulmuştur.")
            k["not"] = " ".join(n for n in notlar if n)
            k["kaynak"] = KAYNAK + f", {ad}"
            if not saglik:
                k["etiketler"] = ["sağlıkla ilgili genel mevzuat"]
            k["id"] = "oz-" + sade(k["baslik"])[:80] + (f"-{sade(k.get('rg_tarih') or k.get('tarih') or '')}" if (k.get("rg_tarih") or k.get("tarih")) else "")
            kayitlar.append({x: y for x, y in k.items() if y})
    gorulen, tekil = set(), []
    for k in kayitlar:
        if k["id"] in gorulen:
            continue
        gorulen.add(k["id"])
        tekil.append(k)
    hedef = KOK / "kaynak-isleme" / "katalog" / "ozcan-halk-sagligi-ekleri.json"
    hedef.write_text(json.dumps(tekil, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    from collections import Counter
    print(len(tekil), "kayıt", dict(Counter(k["tur"] for k in tekil)))


if __name__ == "__main__":
    main()

