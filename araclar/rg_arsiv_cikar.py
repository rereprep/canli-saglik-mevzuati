#!/usr/bin/env python3
"""Eski Resmî Gazete arşiv PDF'lerinden (çok sütunlu, metin katmanlı taramalar) sütun
sırasına uygun metin çıkarır ve segmentler/rg-arsiv.json'daki belgeleri icerik/ altına yazar.
Sütunlar, sayfada boyunca boş kalan dikey şeritlerden bulunur.
Kullanım: python araclar/rg_arsiv_cikar.py
"""
import json, re, sys, unicodedata
from pathlib import Path
import pdfplumber

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import sade  # noqa: E402
from kitaptan_cikar import on_bilgi  # noqa: E402

UST = re.compile(r"(?i)(resm[iîI]\s*gazete|sayfa\s*[:.]|sahife|sa\.?h\.?ife|sayı\s*[:.]\s*\d)")


def sutunlar(sayfa):
    w = sayfa.width
    kelimeler = sayfa.extract_words(keep_blank_chars=False, use_text_flow=False)
    govde = [k for k in kelimeler if sayfa.height * 0.06 < k["top"] < sayfa.height * 0.97]
    if len(govde) < 30:
        return [(0, w)]
    adim = 2.0
    n = int(w / adim) + 1
    dolu = [0] * n
    for k in govde:
        for i in range(int(k["x0"] / adim), min(n, int(k["x1"] / adim) + 1)):
            dolu[i] += 1
    esik = max(2, len(govde) * 0.03)
    bosluklar, bas = [], None
    for i in range(n):
        bos = dolu[i] <= esik
        if bos and bas is None:
            bas = i
        if (not bos or i == n - 1) and bas is not None:
            if (i - bas) * adim >= 6 and bas * adim > w * 0.15 and i * adim < w * 0.85:
                bosluklar.append((bas * adim + i * adim) / 2)
            bas = None
    # Birbirine çok yakın boşlukları ele
    sinirlar = []
    for b in bosluklar:
        if not sinirlar or b - sinirlar[-1] > w * 0.18:
            sinirlar.append(b)
    kenarlar = [0] + sinirlar + [w]
    return [(kenarlar[i], kenarlar[i + 1]) for i in range(len(kenarlar) - 1)]


def sayfa_satirlari(sayfa):
    satirlar = []
    # Sütunları kesen başlık bandı (ör. ortalanmış belge başlığı) varsa sayfayı yatay bölmeden okumak zor;
    # basitçe her sütunu yukarıdan aşağı okuruz.
    for x0, x1 in sutunlar(sayfa):
        kirp = sayfa.crop((x0, 0, x1, sayfa.height), strict=False)
        metin = kirp.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
        for s in metin.split("\n"):
            s = unicodedata.normalize("NFC", s).replace("\u00ad", "-").strip()
            if s:
                satirlar.append(s)
    # Sayfa üst bilgisi (gazete adı, tarih, sayı, sayfa no)
    while satirlar and len(satirlar[0]) < 90 and UST.search(satirlar[0]):
        satirlar.pop(0)
    return satirlar


def bul(satirlar, hedef, bas=0):
    h = sade(hedef)
    if not h:
        return None
    for i in range(bas, len(satirlar)):
        a = sade(satirlar[i])
        if a and (a == h or a.startswith(h[:30]) or (h.startswith(a[:30]) and len(a) > 12)):
            return i
    return None


MADDE = re.compile(r"^((?:Geçici |GEÇİCİ |Ek |EK |Muvakkat )?(?:Madde|MADDE|M\s?A\s?D\s?D\s?E|Mad\.)\s*[\dlIı]+[a-zA-Z/]*)(?:\s*[-–—:.])+\s*")


def markdown(satirlar):
    paragraflar, cari = [], ""
    for s in satirlar:
        yeni = bool(MADDE.match(s)) or (len(s) < 70 and s.isupper())
        if cari and (yeni or re.search(r"[.:;]$", cari) and (s[:1].isupper() or re.match(r"^[a-zçğıöşü]\)|^\(?\d", s))):
            paragraflar.append(cari)
            cari = ""
        if cari.endswith("-") and s[:1].islower():
            cari = cari[:-1] + s
        else:
            cari = (cari + " " + s).strip()
    if cari:
        paragraflar.append(cari)
    cikti = []
    for p in paragraflar:
        m = MADDE.match(p)
        harfler = [c for c in p if c.isalpha()]
        if m:
            cikti.append(f"**{re.sub(r'M ?A ?D ?D ?E', 'MADDE', m.group(1))} –** {p[m.end():]}")
        elif harfler and len(p) < 120 and sum(c.isupper() for c in harfler) / len(harfler) > 0.8:
            cikti.append("### " + p)
        else:
            cikti.append(p)
    return "\n\n".join(cikti) + "\n"


def main():
    segmentler = json.loads((KOK / "kaynak-isleme" / "segmentler" / "rg-arsiv.json").read_text(encoding="utf-8"))
    for seg in segmentler:
        pdf = KOK / "kaynak-isleme" / "indirilen" / seg["kaynak_pdf"]
        satirlar = []
        with pdfplumber.open(pdf) as p:
            for no in range(seg["pdf_baslangic"], seg["pdf_bitis"] + 1):
                if no - 1 < len(p.pages):
                    satirlar += sayfa_satirlari(p.pages[no - 1])
        i = bul(satirlar, seg.get("baslik_satiri", "")) if seg.get("baslik_satiri") else None
        if i is not None:
            satirlar = satirlar[i:]
        if seg.get("sonraki_baslik_satiri"):
            j = bul(satirlar, seg["sonraki_baslik_satiri"], 1)
            if j is not None:
                satirlar = satirlar[:j]
        govde = markdown(satirlar)
        veri = {k: v for k, v in seg.items() if k not in ("baslik_satiri", "sonraki_baslik_satiri")}
        veri["kaynak_pdf_sayfa"] = f"{seg['pdf_baslangic']}-{seg['pdf_bitis']}"
        hedef = KOK / "icerik" / seg["tur"] / f"{seg['id']}.md"
        if hedef.exists() and "\nduzeltildi: true" in hedef.read_text(encoding="utf-8")[:3000]:
            continue
        hedef.write_text(on_bilgi(veri) + govde, encoding="utf-8")
        print(len(govde), i is not None, seg["id"][:60])


if __name__ == "__main__":
    main()
