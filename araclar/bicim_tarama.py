#!/usr/bin/env python3
"""Taranmış (OCR) belgelerde koyu/italik biçimi kaynak sayfalardan aktarır.

Kaynak: kitap PDF'leri (sayfa aralığıyla) ya da kaynak_url'deki taranmış PDF.
Sayfada metin katmanı varsa yazı tipinden, yoksa görüntüden (goruntu_bicim) okunur.
Parçalar araclar/bicim_aktar.uygula ile sitedeki metne işlenir (yalnız birebir eşleşenler).

  python3 araclar/bicim_tarama.py [--yaz] [--id ...] [--sinir N]
"""
import argparse, json, re, sys, time, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bicim_aktar as B, goruntu_bicim as G

KOK = B.KOK; UST = KOK.parent
ONB = UST / "arastirma" / "bicim-tarama"; ONB.mkdir(parents=True, exist_ok=True)
RAPOR = UST / "arastirma" / "bicim-tarama-rapor.json"
logging.getLogger("pdfminer").setLevel(logging.ERROR)
KITAP = [  # (kaynak içinde geçen, dosya, basılı sayfa -> 1 tabanlı PDF sayfası ofseti)
    ("Halk Sağlığı Hizmetleri Mevzuat Kitabı (2025)", "mevzuat-kitabi.pdf", 6),
    ("Mevzuat Kitabı (2022)", "MEVZUAT_KITABI_2022.pdf", 6),
    ("HSGM, 2020", "halk-sagligi-genel-mudurlugu-2020-mevzuat-kitabi-halk-sagligi-hizmetleri-izleme-ve-degerlendirme-personeli-icin.pdf", 6),
    ("Genelgeler Kitabı (2026)", "sb-yonergevegenelge2026pdf.pdf", 14),
    ("Genelgeler Kitabı (2025)", "sbyonergevegenelge202520022025pdf.pdf", 14),
    ("Genelge Kitabı (2024)", "sb-yonerge-ve-genelge-kitabi-2024.pdf", 0),
]


def kelime_kumesi(s):
    return set(w for w in re.findall(r"\w{3,}", s.lower().replace("i̇", "i")))


def sayfa_parcalar(pdf_yol, i, MK=None):
    import pdfplumber, pypdfium2 as pdfium
    with pdfplumber.open(pdf_yol) as pdf:
        pg = pdf.pages[i]
        if len(pg.chars) > 200:
            pg = pg.filter(lambda o: o.get("object_type") != "char" or (abs(o["matrix"][1]) < 0.01 and abs(o["matrix"][2]) < 0.01))
            out = []; onc_top = None
            W_ = pg.extract_words(x_tolerance=1.5, extra_attrs=["fontname"])
            sk = kelime_kumesi(" ".join(w["text"] for w in W_))
            if MK is None or (sk and len(sk & MK) / len(sk) >= 0.3 and len(sk) > 30):
                for w in W_:
                    if onc_top is not None and abs(w["top"] - onc_top) > 3: out.append(("\x00", False, False))
                    onc_top = w["top"]
                    fn = w["fontname"].split("+")[-1]
                    out.append((w["text"] + " ", bool(re.search(r"bold|black|heavy|semibold|demi|,B$", fn, re.I)),
                                bool(re.search(r"italic|oblique|-It$|,I$|BoldIt", fn, re.I))))
                return out + [("\x00", False, False)], "yazı tipi"
    img = pdfium.PdfDocument(str(pdf_yol))[i].render(scale=200 / 72).to_pil().convert("L")
    png = "/tmp/bicim_tarama.png"; img.save(png)
    return G.parcalar(img, png), "görüntü"


def kaynak_sayfalari(v):
    k = v.get("kaynak", "")
    for anahtar, dosya, ofset in KITAP:
        if anahtar in k:
            yol = UST / dosya
            if v.get("kaynak_pdf_sayfa"):
                a, _, b = v["kaynak_pdf_sayfa"].partition("-"); a = int(a); b = int(b or a)
                return yol, list(range(a - 1, b)), False
            m = re.search(r"s\.\s*(\d+)(?:\s*-\s*(\d+))?", k)
            if not m: return None, [], False
            a = int(m.group(1)); b = int(m.group(2) or a)
            if "HSGM, 2020" in anahtar:  # ofset doğrulanmadı: pencere + örtüşme süzgeci
                return yol, list(range(a + ofset - 1 - 3, b + ofset - 1 + 4)), True
            return yol, list(range(a + ofset - 1, b + ofset)), False
    u = v.get("kaynak_url", "")
    if ".gov.tr" in u:
        for uz in ("pdf",):
            yol = B.ONB / f"{v['id']}.{uz}"
            if yol.exists(): return yol, None, False
        try:
            v2 = dict(v); v2.pop("ocr", None)
            t = "pdf" if u.lower().split("?")[0].endswith(".pdf") else "sayfa"
            yol = ONB / f"{v['id']}.kaynak"
            if not yol.exists():
                q = B.al(u)
                if b"%PDF" not in q[:1024] and t == "sayfa":
                    sayfa = q.decode("utf-8", "ignore")
                    bag = [x for x in re.findall(r'href="([^"]+\.pdf)"', sayfa, re.I)
                           if not re.search(r"cerez|kvkk|kisisel|politika|aydinlatma", x, re.I)]
                    if not bag: return None, [], False
                    import urllib.parse, html as H
                    q = B.al(urllib.parse.urljoin(u, H.unescape(bag[0])))
                yol.write_bytes(q); time.sleep(0.5)
            if b"%PDF" not in yol.read_bytes()[:1024]: return None, [], False
            return yol, None, False
        except Exception as e:
            return None, [], False
    return None, [], False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaz", action="store_true"); ap.add_argument("--id", nargs="*"); ap.add_argument("--sinir", type=int, default=0)
    ap.add_argument("--goster", action="store_true")
    a = ap.parse_args()
    rapor = json.loads(RAPOR.read_text()) if RAPOR.exists() else {}
    import pypdfium2 as pdfium
    say = 0
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        if a.id and not any(md.stem.startswith(x) for x in a.id): continue
        v, h, b = B.on_bilgi(md)
        if not v or v.get("ocr") != "true" or len(b.strip()) < 200: continue
        if a.sinir and say >= a.sinir: break
        say += 1
        r = rapor.setdefault(md.stem, {})
        try:
            onb = ONB / f"{md.stem}.json"
            if onb.exists():
                P = [tuple(x) for x in json.loads(onb.read_text())]; r.setdefault("durum", "önbellek")
            else:
                v["id"] = md.stem
                yol, sayfalar, pencere = kaynak_sayfalari(v); kitap = "Kitab" in v.get("kaynak", "")
                if not yol or not yol.exists():
                    r["durum"] = "kaynak yok"; continue
                n = len(pdfium.PdfDocument(str(yol)))
                if sayfalar is None: sayfalar = list(range(min(n, 40)))
                sayfalar = [i for i in sayfalar if 0 <= i < n]
                MK = kelime_kumesi(b); P = []; yontem = set(); alinan = []
                for i in sayfalar:
                    pp, ytm = sayfa_parcalar(yol, i, MK)
                    if pencere or (len(sayfalar) > 3 and not kitap):
                        sk = kelime_kumesi(" ".join(t for t, _, _ in pp))
                        if not sk or len(sk & MK) / len(sk) < (0.5 if pencere else 0.35): continue
                    P += pp; yontem.add(ytm); alinan.append(i)
                onb.write_text(json.dumps(P, ensure_ascii=False))
                r.update(yontem=sorted(yontem), sayfalar=alinan)
            kos = B.bicimli_kosular(P)
            toplam = sum(len(t) for t, _, _ in kos)
            if toplam > 0.6 * max(1, len(b)):
                r.update(durum="çok fazla biçim, atlandı"); continue
            yeni, n = B.uygula(b, kos, kati=True)
            r.update(durum="ok", kosu=len(kos), eslesen=n)
            if a.goster:
                print("##", md.stem, r.get("yontem"), "koşu", len(kos), "eşleşen", n)
                for t, k, i in kos[:10]: print("   ", "K" if k else " ", "İ" if i else " ", t[:90])
            if a.yaz and n:
                md.write_text(h + yeni, encoding="utf-8")
        except Exception as e:
            r["hata"] = str(e)[:150]
        if say % 20 == 0:
            RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=0)); print(say, "belge", flush=True)
    RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=0))
    from collections import Counter
    print(say, "belge;", dict(Counter(x.get("durum", "-") for x in rapor.values())),
          "eşleşen:", sum(x.get("eslesen", 0) for x in rapor.values()), "hata:", sum(1 for x in rapor.values() if "hata" in x))


if __name__ == "__main__":
    main()

