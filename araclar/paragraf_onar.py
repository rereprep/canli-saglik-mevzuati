#!/usr/bin/env python3
"""Satır sonlarından bölünmüş paragrafları kaynağın paragraf yapısına göre birleştirir.

Aday: ardışık iki düz paragraf; ilki noktalama ile bitmiyor. Karar:
  1) Kaynakta (HTML/DOCX paragrafları, PDF metin katmanı ya da taranmış sayfanın satır konumları)
     iki parçanın birleşim yeri bulunursa: arada paragraf sınırı yoksa birleştir, varsa bırak.
  2) Kaynakta bulunamazsa: ikinci parça küçük harfle başlıyor ve ilk parça liste maddesi değilse birleştir.
  python3 araclar/paragraf_onar.py [--yaz] [--id ...]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bicim_aktar as B

KOK = B.KOK; UST = KOK.parent
TAR = UST / "arastirma" / "bicim-tarama"
TRAP = UST / "arastirma" / "bicim-tarama-rapor.json"
RAPOR = UST / "arastirma" / "paragraf-onar-rapor.json"
SON = re.compile(r"[.;:!?…)”\"\]]$")
LISTE = re.compile(r"^([a-zçğıöşü]|[0-9]+(\.[0-9]+)*|[IVX]+)[.)-]\s|^\(\d+\)|^[-•–]\s")
AYRI_SON = re.compile(r"^(ifade eder|denir|anlaşılır|olarak tanımlanır|kısaltmaları ifade eder)")


def duz(x):
    return re.sub(r"\*\*|</?i>", "", x).strip()


ETIKET = re.compile(r"^(Sayı|SAYI|Konu|KONU|İlgi|İLGİ|Ek|EK|Ekler|EKLER|Dağıtım|DAĞITIM|Gereği|GEREĞİ|Bilgi|BİLGİ|Tarih|TARİH)\s*[:：]")


def buyuk_oran(s):
    h = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in h) / len(h) if h else 0


def sik(s):
    return re.sub(r"[^\wçğıöşüÇĞİÖŞÜâîûÂÎÛ]", "", s.lower().replace("i̇", "i"))


class Kaynak:
    """Kaynağı 'paragraf' listesine indirger; birleşim yerinin aynı paragrafta olup olmadığını söyler."""
    def __init__(self, paragraflar):
        self.metin = ""; self.sinir = []  # sinir[k]: k. karakter yeni paragrafın başı mı
        for p in paragraflar:
            c = sik(p)
            if not c: continue
            self.sinir.extend([True] + [False] * (len(c) - 1)); self.metin += c

    def karar(self, onceki, sonraki):
        a = sik(onceki)[-30:]; b = sik(sonraki)[:30]
        if len(a) < 8 or len(b) < 6: return None
        i = self.metin.find(a + b)
        if i < 0 or self.metin.find(a + b, i + 1) >= 0: return None
        return not self.sinir[i + len(a)]  # True: aynı paragraf -> birleştir


def html_par(yol):
    P = B.html_parcalar(yol); out = [""]
    for t, _, _ in P:
        for j, x in enumerate(t.split("\x00")):
            if j: out.append("")
            out[-1] += x
    return out


def docx_par(yol):
    from docx import Document
    return [p.text for p in Document(str(yol)).paragraphs]


def satirlardan_par(satirlar):
    """satirlar: [(x0, x1, ust, alt, metin)] sayfa sırasıyla. Girinti/kısa satır/boşluğa göre paragraflar."""
    if not satirlar: return []
    xs = sorted(s[0] for s in satirlar); sol = xs[len(xs) // 10]
    sag = sorted(s[1] for s in satirlar)[-max(1, len(satirlar) // 10)]
    gen = max(1.0, sag - sol)
    yuks = sorted(s[3] - s[2] for s in satirlar)[len(satirlar) // 2] or 1
    out = []; onc = None
    for s in satirlar:
        yeni = onc is None
        if onc is not None:
            if s[0] - sol > 0.025 * gen: yeni = True              # girintili başlangıç
            if onc[1] < sag - 0.12 * gen: yeni = True             # önceki satır kısa kaldı
            if s[2] - onc[3] > 1.2 * yuks or s[2] < onc[2]: yeni = True  # boşluk / yeni sütun-sayfa
        if yeni: out.append(s[4])
        else: out[-1] += " " + s[4]
        onc = s
    return out


def pdf_par(yol, sayfalar=None):
    import pdfplumber, logging
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    out = []
    with pdfplumber.open(str(yol)) as pdf:
        idx = sayfalar if sayfalar is not None else range(len(pdf.pages))
        for i in idx:
            if i >= len(pdf.pages): continue
            pg = pdf.pages[i]
            if len(pg.chars) < 200:
                out += goruntu_par(yol, i); continue
            W = pg.extract_words(x_tolerance=1.5)
            sat = []
            for w in sorted(W, key=lambda w: (round(w["top"] / 3), w["x0"])):
                if sat and abs(sat[-1][2] - w["top"]) < 3:
                    s = sat[-1]; sat[-1] = (s[0], max(s[1], w["x1"]), s[2], max(s[3], w["bottom"]), s[4] + " " + w["text"])
                else:
                    sat.append((w["x0"], w["x1"], w["top"], w["bottom"], w["text"]))
            out += satirlardan_par(sat)
    return out


def goruntu_par(yol, i):
    import pypdfium2 as pdfium
    png = "/tmp/paragraf_onar.png"
    pdfium.PdfDocument(str(yol))[i].render(scale=200 / 72).to_pil().save(png)
    o = subprocess.run(["/tmp/ocrkutu", png], capture_output=True, text=True).stdout
    sat = {}
    for l in o.splitlines():
        p = l.split("\t")
        if p[0] != "K" or len(p) < 7: continue
        li = int(p[1]); x, y, w, h = map(float, p[2:6])
        s = sat.get(li)
        sat[li] = (min(s[0], x) if s else x, max(s[1], x + w) if s else x + w, 1 - y - h if not s else min(s[2], 1 - y - h),
                   1 - y if not s else max(s[3], 1 - y), (s[4] + " " if s else "") + p[6])
    return satirlardan_par([sat[k] for k in sorted(sat)])


def kaynak_bul(md, v, tarama_rapor):
    k = md.stem
    for uz in ("html", "docx", "pdf"):
        yol = B.ONB / f"{k}.{uz}"
        if yol.exists():
            if uz == "html": return Kaynak(html_par(yol))
            if uz == "docx": return Kaynak(docx_par(yol))
            return Kaynak(pdf_par(yol))
    r = tarama_rapor.get(k, {})
    yol = TAR / f"{k}.kaynak"
    if yol.exists() and b"%PDF" in yol.read_bytes()[:1024]:
        return Kaynak(pdf_par(yol, r.get("sayfalar")))
    import bicim_tarama as T
    for anahtar, dosya, _ in T.KITAP:
        if anahtar in v.get("kaynak", "") and r.get("sayfalar"):
            return Kaynak(pdf_par(UST / dosya, r["sayfalar"]))
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--yaz", action="store_true"); ap.add_argument("--id", nargs="*")
    ap.add_argument("--goster", action="store_true"); ap.add_argument("--kaynaksiz", action="store_true", help="kaynak açmadan yalnız kesin kural")
    a = ap.parse_args()
    trap = json.loads(TRAP.read_text()) if TRAP.exists() else {}
    rapor = {}; top = {"kaynak_birlestir": 0, "kaynak_ayri": 0, "kural_birlestir": 0, "karar_yok": 0}
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        if a.id and not any(md.stem.startswith(x) for x in a.id): continue
        v, h, b = B.on_bilgi(md)
        if not v: continue
        bl = re.split(r"\n{2,}", b.strip())
        adaylar = []
        for i in range(len(bl) - 1):
            x, y = bl[i].strip(), bl[i + 1].strip()
            if "\n" in x or "\n" in y: continue
            if x.startswith(("#", "|", "<", "---")) or y.startswith(("#", "|", "<", "---", "**")): continue
            if re.match(r"^\*\*[^*]{1,80}\*\*$", x): continue
            dx, dy = duz(x), duz(y)
            if len(dx) < 30 or SON.search(dx) or not dy: continue
            if LISTE.match(dy) or AYRI_SON.match(dy): continue
            if ETIKET.match(dx) or ETIKET.match(dy): continue
            if re.match(r"^[\d(]", dy) or re.match(r"^\d+\s", dx): continue  # tablo satırı / numaralı öğe
            if re.search(r"\d$", dx): continue
            if len(re.findall(r"\d", dx + dy)) > 0.15 * len(dx + dy): continue  # sayı ağırlıklı (tablo)
            if buyuk_oran(dy.split(" ")[0] + " " + " ".join(dy.split(" ")[1:4])) > 0.8 and buyuk_oran(dy) > 0.5: continue
            if buyuk_oran(dx) > 0.45 or buyuk_oran(dy) > 0.45: continue
            adaylar.append(i)
        if not adaylar: continue
        kay = None
        if not a.kaynaksiz:
            try: kay = kaynak_bul(md, v, trap)
            except Exception as e: rapor.setdefault(md.stem, {})["hata"] = str(e)[:100]
        birles = set()
        for i in adaylar:
            dx, dy = duz(bl[i]), duz(bl[i + 1])
            k = kay.karar(dx, dy) if kay else None
            if k is True: birles.add(i); top["kaynak_birlestir"] += 1
            elif k is False: top["kaynak_ayri"] += 1
            elif dy[:1].islower() and not LISTE.match(duz(bl[i])): birles.add(i); top["kural_birlestir"] += 1
            else: top["karar_yok"] += 1
        if not birles: continue
        yeni = []; j = 0
        while j < len(bl):
            p = bl[j]
            while j in birles:
                p = p.rstrip() + " " + bl[j + 1].strip(); j += 1
            yeni.append(p); j += 1
        rapor[md.stem] = {"aday": len(adaylar), "birlesen": len(birles), "kaynak": bool(kay)}
        if a.goster:
            print("##", md.stem, rapor[md.stem])
            for i in sorted(birles)[:4]: print("    +", duz(bl[i])[-35:], "|", duz(bl[i + 1])[:35])
        if a.yaz:
            md.write_text(h + "\n" + "\n\n".join(yeni) + "\n", encoding="utf-8")
    RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=0))
    print(len(rapor), "belge;", top)


if __name__ == "__main__":
    main()

