#!/usr/bin/env python3
"""Segment JSON dosyalarındaki sayfa aralıklarını kaynak PDF'lerden okuyup
icerik/<tur>/<id>.md dosyalarına yazar.

Satır konumu ve yazı boyutu kullanılarak paragraf, başlık ve dipnotlar ayrılır;
sayfa üst/alt bilgileri atılır.

Kullanım: python araclar/kitaptan_cikar.py --kaynak-dizin "<pdf klasörü>" [segment.json ...]
"""
import argparse, json, re, statistics, sys, unicodedata
from collections import Counter
from pathlib import Path

import pdfplumber

KOK = Path(__file__).resolve().parent.parent
TURLER = {"kanun", "cbk", "khk", "tuzuk", "yonetmelik", "yonerge", "genelge", "teblig", "protokol", "yazi"}
ALANLAR = ["id", "baslik", "tur", "tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu",
           "etiketler", "kaynak", "kaynak_url", "not", "durum", "degisiklikler", "ocr", "duzeltildi"]

UST_BILGI = re.compile(r"(SAĞLIK BAKANLIĞI YÖNERGELER VE GENELGELER KİTABI|^\d{1,4}$|^[ivxlc]{1,6}$)", re.I)
MADDE = re.compile(r"^((?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+[/A-Za-z]*)\s*[-–—:]\s*")
BOLUM = re.compile(r"^([A-ZÇĞİÖŞÜ]+ )?(BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU|ON[A-ZÇĞİÖŞÜ]+|YİRMİ[A-ZÇĞİÖŞÜ]*)\s+(BÖLÜM|KISIM)\b")
MADDE_ISARETI = re.compile(r"^(\(\d+\)|\d+[\.\)]\s|[a-zçğıöşü]{1,2}\)\s|[IVX]+[\.\-]\s|[-–•▪●■◦]\s?)")


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip()


def anahtar(s):
    s = norm(s).casefold().replace("i̇", "i")
    return re.sub(r"[^0-9a-zçğıöşü]", "", s)


def karakterden_metin(karakterler, boyut):
    """Karakter konumlarından boşlukları yeniden kurar; üst simge dipnot işaretlerini atar."""
    parcalar, onceki = [], None
    kucuk = ""

    def kucuk_bosalt():
        nonlocal kucuk
        if re.fullmatch(r"\[\d{1,3}\]", kucuk):
            parcalar.append("<sup>" + kucuk + "</sup>")
        kucuk = ""

    for c in karakterler:
        if not c["text"].strip():
            if parcalar and parcalar[-1] != " ":
                parcalar.append(" ")
            continue
        if c["size"] < boyut * 0.75:
            kucuk += c["text"]
            continue
        kucuk_bosalt()
        if onceki is not None and c["x0"] - onceki["x1"] > min(c["size"], onceki["size"]) * 0.18:
            if parcalar and parcalar[-1] != " ":
                parcalar.append(" ")
        parcalar.append(c["text"])
        onceki = c
    kucuk_bosalt()
    return norm("".join(parcalar))


class Satir:
    __slots__ = ("metin", "x0", "x1", "top", "boyut", "dipnot", "sayfa_genislik", "sol")

    def __init__(self, **k):
        for a, b in k.items():
            setattr(self, a, b)


class PdfOnbellek:
    def __init__(self, dizin):
        self.dizin = Path(dizin)
        self.acik = {}
        self.cache = {}

    def satirlar(self, ad, no):
        key = (ad, no)
        if key in self.cache:
            return self.cache[key]
        if ad not in self.acik:
            self.acik[ad] = pdfplumber.open(self.dizin / ad)
        pdf = self.acik[ad]
        if no < 1 or no > len(pdf.pages):
            return []
        sayfa = pdf.pages[no - 1]
        if len((sayfa.extract_text() or "").strip()) < 80:
            sonuc = self.ocr_satirlari(ad, no, sayfa)
            if sonuc is not None:
                self.cache[key] = sonuc
                return sonuc
        ham = sayfa.extract_text_lines(return_chars=True, strip=True)
        boyutlar = Counter()
        for l in ham:
            for c in l["chars"]:
                if c["text"].strip():
                    boyutlar[round(c["size"])] += 1
        govde = boyutlar.most_common(1)[0][0] if boyutlar else 10
        sonuc = []
        for l in ham:
            karakterler = [c for c in l["chars"]]
            ana = [c["size"] for c in karakterler if c["text"].strip()]
            if not ana:
                continue
            boyut = statistics.median(ana)
            metin = karakterden_metin(karakterler, boyut)
            if not metin:
                continue
            if (l["top"] < 55 or l["top"] > sayfa.height - 65) and (UST_BILGI.search(metin) or len(metin) < 5):
                continue
            sonuc.append(Satir(metin=metin, x0=l["x0"], x1=l["x1"], top=l["top"], boyut=boyut,
                               dipnot=boyut < govde - 0.6 and l["top"] > sayfa.height * 0.45,
                               sayfa_genislik=sayfa.width, sol=0))
        govde_sol = [s.x0 for s in sonuc if not s.dipnot]
        sol = min(govde_sol) if govde_sol else 70
        for s in sonuc:
            s.sol = sol
        # Dipnot bloğu: ilk dipnot satırından sonrası
        ilk = next((i for i, s in enumerate(sonuc) if s.dipnot), None)
        if ilk is not None:
            for s in sonuc[ilk:]:
                if s.boyut < govde - 0.6:
                    s.dipnot = True
        self.cache[key] = sonuc
        return sonuc

    def ocr_satirlari(self, ad, no, sayfa):
        """araclar/ocr_toplu.py çıktısını satır listesine çevirir (yoksa None)."""
        yol = KOK / "kaynak-isleme" / "ocr" / Path(ad).stem / f"{no:04d}.json"
        if not yol.exists():
            return None
        self.ocr_kullanildi = True
        w, h = float(sayfa.width), float(sayfa.height)
        ham = sorted(json.loads(yol.read_text(encoding="utf-8"))["lines"], key=lambda l: (l["top"], l["x0"]))
        # Aynı yükseklikteki parçaları (tablo hücreleri) tek satırda birleştir
        gruplar = []
        for l in ham:
            if gruplar and abs(l["top"] - gruplar[-1][0]["top"]) < 0.006:
                gruplar[-1].append(l)
            else:
                gruplar.append([l])
        sonuc = []
        for g in gruplar:
            g.sort(key=lambda l: l["x0"])
            metin = norm("   ".join(l["text"] for l in g))
            top = g[0]["top"] * h
            if not metin or ((top < 55 or top > h - 65) and (UST_BILGI.search(metin) or len(metin) < 5)):
                continue
            sonuc.append(Satir(metin=metin, x0=g[0]["x0"] * w, x1=g[-1]["x1"] * w, top=top, boyut=10,
                               dipnot=False, sayfa_genislik=w, sol=0))
        # OCR'da sol kenar: en sık görülen satır başı (başlıklar ve girintiler hariç)
        sayac = Counter(round(s.x0 / 4) * 4 for s in sonuc)
        sol = sayac.most_common(1)[0][0] if sayac else 70
        sol = min([s.x0 for s in sonuc if abs(s.x0 - sol) <= 6] or [sol])
        for s in sonuc:
            s.sol = sol
        return sonuc


def bul(satirlar, hedef):
    h = anahtar(hedef)
    if not h:
        return None
    for i, s in enumerate(satirlar):
        a = anahtar(s.metin)
        if a and (a == h or a.startswith(h[:40]) or (h.startswith(a[:40]) and len(a) > 15)):
            return i
    return None


def segment_satirlari(seg, pdfler):
    govde, dipnot = [], []
    bas, bit = int(seg["pdf_baslangic"]), int(seg["pdf_bitis"])
    for no in range(bas, bit + 1):
        satirlar = list(pdfler.satirlar(seg["kaynak_pdf"], no))
        if no == bas and seg.get("baslik_satiri"):
            i = bul(satirlar, seg["baslik_satiri"])
            if i is not None:
                satirlar = satirlar[i:]
        if no == bit and seg.get("sonraki_baslik_satiri"):
            i = bul(satirlar, seg["sonraki_baslik_satiri"])
            if i is not None:
                satirlar = satirlar[:i]
        for s in satirlar:
            (dipnot if s.dipnot else govde).append(s)
        if govde:
            govde.append(None)  # sayfa sonu işareti
    return govde, dipnot


def buyuk_harf_mi(s):
    harfler = [c for c in s if c.isalpha()]
    return len(harfler) >= 4 and sum(c.isupper() for c in harfler) / len(harfler) > 0.9


def ortali_mi(s):
    sag = s.sayfa_genislik - s.sol
    return s.x0 - s.sol > 40 and abs((s.x0 - s.sol) - (sag - s.x1)) < 30


def birlestir(onceki, yeni):
    if re.search(r"[a-zçğıöşü]-$", onceki) and re.match(r"^[a-zçğıöşü]", yeni):
        return onceki[:-1] + yeni
    return onceki + " " + yeni


def paragraflar(satirlar):
    bloklar = []  # [tip, metin]
    sayfa_sonu = False
    for s in satirlar:
        if s is None:
            sayfa_sonu = True
            continue
        t = s.metin
        girinti = s.x0 - s.sol > 12
        if BOLUM.match(t) or (buyuk_harf_mi(t) and len(t) < 140) or (ortali_mi(s) and len(t) < 120 and not t.endswith((",", ";"))):
            if bloklar and bloklar[-1][0] == "baslik" and not sayfa_sonu and not BOLUM.match(t):
                bloklar[-1][1] += " " + t
            else:
                bloklar.append(["baslik", t])
            sayfa_sonu = False
            continue
        yeni = girinti or MADDE.match(t) or MADDE_ISARETI.match(t) or not bloklar or bloklar[-1][0] == "baslik"
        if not yeni and sayfa_sonu and re.search(r"[.:]$", bloklar[-1][1]) and re.match(r"^[A-ZÇĞİÖŞÜ(]", t):
            yeni = True
        if yeni:
            bloklar.append(["p", t])
        else:
            bloklar[-1][1] = birlestir(bloklar[-1][1], t)
        sayfa_sonu = False
    return bloklar


def markdowna(govde, dipnotlar):
    bloklar = paragraflar(govde)
    cikti = []
    for i, (tip, metin) in enumerate(bloklar):
        sonraki = bloklar[i + 1][1] if i + 1 < len(bloklar) else ""
        if tip == "baslik":
            cikti.append(("## " if BOLUM.match(metin) or not cikti else "### ") + metin)
            continue
        m = MADDE.match(metin)
        if m:
            cikti.append(f"**{norm(m.group(1))} –** {metin[m.end():]}".rstrip())
        elif MADDE.match(sonraki) and len(metin) < 110 and not re.search(r"[.:;,]$", metin):
            cikti.append("#### " + metin)
        else:
            cikti.append(metin)
    if dipnotlar:
        dn = []
        for s in dipnotlar:
            if re.match(r"^\[?\d+\]?\s", s.metin) or not dn:
                dn.append(s.metin)
            else:
                dn[-1] = birlestir(dn[-1], s.metin)
        cikti.append("---\n\n**Dipnotlar**\n\n" + "\n\n".join("<small>" + d + "</small>" for d in dn))
    return "\n\n".join(cikti) + "\n"


def on_bilgi(seg):
    satirlar = ["---"]
    for alan in ALANLAR:
        if alan in seg and seg[alan] not in (None, "", []):
            satirlar.append(f"{alan}: {json.dumps(seg[alan], ensure_ascii=False)}")
    satirlar.append("---")
    return "\n".join(satirlar) + "\n\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak-dizin", required=True)
    ap.add_argument("segmentler", nargs="*")
    a = ap.parse_args()
    dosyalar = a.segmentler or sorted(str(p) for p in (KOK / "kaynak-isleme" / "segmentler").glob("*.json"))
    pdfler = PdfOnbellek(a.kaynak_dizin)
    goruldu, hatalar, yazilan = set(), [], 0
    for d in dosyalar:
        for seg in json.load(open(d, encoding="utf-8")):
            sid = seg.get("id")
            if seg.get("tur") not in TURLER:
                hatalar.append(f"{d}: {sid}: geçersiz tür {seg.get('tur')!r}")
                continue
            if sid in goruldu:
                hatalar.append(f"{d}: yinelenen id {sid}")
                continue
            goruldu.add(sid)
            hedef = KOK / "icerik" / seg["tur"] / f"{sid}.md"
            if hedef.exists() and "\nduzeltildi: true\n" in hedef.read_text(encoding="utf-8")[:3000]:
                continue  # ajan/insan tarafından düzeltilmiş metni ezme
            pdfler.ocr_kullanildi = False
            govde, dipnot = segment_satirlari(seg, pdfler)
            if not any(govde):
                hatalar.append(f"{d}: {sid}: boş metin")
                continue
            seg.setdefault("durum", "yürürlükte")
            if pdfler.ocr_kullanildi:
                seg["ocr"] = True
            seg["kaynak_pdf_sayfa"] = f"{seg['pdf_baslangic']}-{seg['pdf_bitis']}"
            hedef = KOK / "icerik" / seg["tur"] / f"{sid}.md"
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_text(on_bilgi(seg) + markdowna(govde, dipnot), encoding="utf-8")
            yazilan += 1
    print(f"{yazilan} belge yazıldı")
    for h in hatalar:
        print("UYARI:", h, file=sys.stderr)


if __name__ == "__main__":
    main()

