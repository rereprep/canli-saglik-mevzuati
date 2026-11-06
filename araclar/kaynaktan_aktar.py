#!/usr/bin/env python3
"""Ajanların bulduğu resmî kaynak adreslerinden künye kayıtlarının tam metnini alır.

Girdi: ../arastirma/sonuc*.json  ([{"id", "url", "yedek_url", ...}])
- PDF: kaynak-isleme/indirilen/kunye/ altına indirilir, segmentler/kunye-kaynak.json'a
  segment yazılır (metin kitaptan_cikar.py ile, taranmışsa ocr_toplu.py ile çıkarılır).
- DOC/DOCX/ZIP: Word metni doğrudan icerik/<tür>/ altına yazılır.
- HTML: saglik.gov.tr sayfa gövdesi ya da Resmî Gazete metni yazılır; sayfada
  PDF/Word eki varsa önce ek denenir.
İndirilen metin başlıkla karşılaştırılır; eşleşmeyenler atlanır ve raporlanır.

Kullanım: python araclar/kaynaktan_aktar.py [--arastirma ../arastirma]
"""
import argparse, html, io, json, re, subprocess, sys, urllib.parse, urllib.request, zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import belgeleri_oku, sade, baslik_ozu  # noqa: E402
from saglik_gov_aktar import docx_yaz, html_yaz, SOFFICE  # noqa: E402
from mevzuat_gov_aktar import html_md  # noqa: E402

KLASOR = KOK / "kaynak-isleme" / "indirilen" / "kunye"
SEGMENT = KOK / "kaynak-isleme" / "segmentler" / "kunye-kaynak.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) CanliSaglikMevzuati"}


def getir(url):
    url = urllib.parse.quote(url, safe=":/?&=%#+~.,-_")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def coz(ham):
    for kod in ("utf-8", "windows-1254"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            pass
    return ham.decode("utf-8", "replace")


def tip_bul(ham):
    if ham[:4] == b"%PDF":
        return "pdf"
    if ham[:4] == b"PK\x03\x04":
        try:
            adlar = zipfile.ZipFile(io.BytesIO(ham)).namelist()
        except zipfile.BadZipFile:
            return ""
        return "docx" if "word/document.xml" in adlar else "zip"
    if ham[:8] == bytes.fromhex("D0CF11E0A1B11AE1"):
        return "doc"
    if ham[:3] == b"\xff\xd8\xff" or ham[:4] == b"\x89PNG":
        return "resim"
    return "html"


def kaynak_adi(url):
    h = urllib.parse.urlparse(url).netloc
    if "resmigazete" in h:
        return "Resmî Gazete (ilk yayımlanan metin; sonraki değişiklikler işlenmemiş olabilir)"
    if "saglik.gov.tr" in h:
        return f"T.C. Sağlık Bakanlığı internet sitesi ({h.removeprefix('www.')})"
    if "tbmm" in h:
        return "TBMM kanun metni (ilk kabul edilen metin)"
    return f"Resmî kurum sitesi ({h.removeprefix('www.')})"


def eslesir(b, metin):
    """İndirilen metin bu belgeye mi ait? Başlık sözcüklerinin çoğu metnin başında geçmeli."""
    ozu = [s for s in baslik_ozu(b).split() if len(s) > 3]
    if not ozu:
        return True
    bas = sade(metin[:6000])
    return sum(s[:6] in bas for s in ozu) / len(ozu) >= 0.6


def pdf_metni(yol, sayfa=3):
    import pdfplumber
    with pdfplumber.open(yol) as p:
        return len(p.pages), "\n".join((p.pages[i].extract_text() or "") for i in range(min(sayfa, len(p.pages))))


def word_yaz(yol, veri):
    if yol.suffix.lower() == ".doc":
        cikti = yol.with_suffix(".docx")
        if not cikti.exists():
            subprocess.run([SOFFICE, "--headless", "--convert-to", "docx", "--outdir", str(yol.parent), str(yol)],
                           capture_output=True, timeout=180)
        if not cikti.exists():
            subprocess.run(["textutil", "-convert", "docx", "-output", str(cikti), str(yol)], capture_output=True, timeout=120)
        yol = cikti
    return yol.exists() and docx_yaz(yol, veri)


def ekleri_bul(sayfa, url):
    ekler = []
    for m in re.finditer(r'href="([^"]+\.(?:pdf|docx?|zip)(?:\?[^"]*)?)"', sayfa, re.I):
        u = urllib.parse.urljoin(url, html.unescape(m.group(1)))
        if u not in ekler:
            ekler.append(u)
    return ekler


def capa_bolumu(sayfa, capa):
    """Eski tek sayfalık Resmî Gazete'de <a name="N"> çapasından sonrakine kadar olan kısım."""
    m = re.search(rf'(?i)<a[^>]+name="?{re.escape(capa)}"?[ >]', sayfa)
    if not m:
        return ""
    son = re.search(r'(?i)<a[^>]+name="?\d+"?[ >]', sayfa[m.end():])
    return sayfa[m.start(): m.end() + son.start() if son else len(sayfa)]


def isle(b, url, segmentler, rapor, derinlik=0, zorla=False, baslik=None):
    veri = {k: b.get(k) for k in ("id", "baslik", "tur", "tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu",
                                  "etiketler", "not", "durum")}
    if baslik:
        veri["baslik"] = baslik
    veri.update(kaynak=kaynak_adi(url), kaynak_url=url)
    veri = {k: v for k, v in veri.items() if v not in (None, "", [])}
    try:
        ham = getir(url)
    except Exception as hata:
        rapor.append((b["id"], url, f"indirilemedi: {hata}"))
        return False
    tip = tip_bul(ham)
    KLASOR.mkdir(parents=True, exist_ok=True)
    if tip == "zip":
        z = zipfile.ZipFile(io.BytesIO(ham))
        adaylar = sorted((n for n in z.namelist() if re.search(r"\.(pdf|docx?)$", n, re.I)),
                         key=lambda n: -z.getinfo(n).file_size)
        for n in adaylar:
            ham, tip = z.read(n), tip_bul(z.read(n))
            break
        else:
            rapor.append((b["id"], url, "zip içinde belge yok"))
            return False
    if tip == "pdf":
        yol = KLASOR / f"{b['id'][:80]}.pdf"
        yol.write_bytes(ham)
        n, ilk = pdf_metni(yol)
        if len(ilk.strip()) > 200 and not zorla and not eslesir(b, ilk):
            rapor.append((b["id"], url, "PDF başka belgeye ait görünüyor"))
            return False
        segmentler[b["id"]] = {**veri, "kaynak_pdf": f"kunye/{yol.name}", "pdf_baslangic": 1, "pdf_bitis": n}
        rapor.append((b["id"], url, "PDF segmenti" + (" (taranmış, OCR gerekir)" if len(ilk.strip()) < 200 else "")))
        return True
    if tip in ("doc", "docx"):
        yol = KLASOR / f"{b['id'][:80]}.{tip}"
        yol.write_bytes(ham)
        try:
            tamam = word_yaz(yol, veri)
        except Exception as hata:
            rapor.append((b["id"], url, f"Word okunamadı: {hata}"))
            return False
        if not tamam:
            # Metni olmayan (içine taranmış sayfa konmuş) Word dosyası: PDF'e çevir, OCR'lanacak
            subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(KLASOR), str(yol)],
                           capture_output=True, timeout=180)
            pdf = yol.with_suffix(".pdf")
            if pdf.exists():
                n, _ = pdf_metni(pdf, 1)
                segmentler[b["id"]] = {**veri, "kaynak_pdf": f"kunye/{pdf.name}", "pdf_baslangic": 1, "pdf_bitis": n}
                rapor.append((b["id"], url, "Word içinde taranmış sayfa: PDF segmenti (OCR gerekir)"))
                return True
        hedef = KOK / "icerik" / b["tur"] / f"{b['id']}.md"
        if tamam and not eslesir(b, hedef.read_text(encoding="utf-8").split("\n---\n", 1)[-1]):
            hedef.unlink()
            rapor.append((b["id"], url, "Word dosyası başka belgeye ait görünüyor"))
            return False
        rapor.append((b["id"], url, "Word metni" if tamam else "Word metni kısa/boş"))
        return tamam
    if tip == "html":
        sayfa = coz(ham)
        host = urllib.parse.urlparse(url).netloc
        if "mevzuat.gov.tr" in host:
            rapor.append((b["id"], url, "mevzuat.gov.tr sayfası (kaldırılmış)"))
            return False
        if derinlik == 0 and "saglik.gov.tr" in host:
            for ek in ekleri_bul(sayfa, url)[:3]:
                if isle(b, ek, segmentler, rapor, derinlik + 1):
                    return True
        if "resmigazete" in host:
            if "#" in url:
                sayfa = capa_bolumu(sayfa, url.rsplit("#", 1)[1])
            elif derinlik == 0 and re.search(r"/\d{8}\.htm$", url):
                # Günlük fihrist sayfası: başlığa en çok benzeyen bağlantıyı izle
                import difflib
                en, puan = None, 0
                for m in re.finditer(r'(?is)<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', sayfa):
                    ad = sade(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))))
                    p = difflib.SequenceMatcher(None, baslik_ozu(b), ad).ratio()
                    if p > puan:
                        en, puan = urllib.parse.urljoin(url, m.group(1)), p
                if en and puan >= 0.6 and en != url:
                    return isle(b, en, segmentler, rapor, derinlik + 1)
                rapor.append((b["id"], url, "fihrist sayfasında belge bağlantısı bulunamadı"))
                return False
            govde = html_md(sayfa)
            if len(govde) > 400 and (zorla or eslesir(b, govde)):
                on = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in veri.items()] + ["---"]
                (KOK / "icerik" / b["tur"] / f"{b['id']}.md").write_text("\n".join(on) + "\n\n" + govde, encoding="utf-8")
                rapor.append((b["id"], url, "Resmî Gazete metni"))
                return True
        elif "saglik.gov.tr" in host:
            if html_yaz(sayfa, veri):
                hedef = KOK / "icerik" / b["tur"] / f"{b['id']}.md"
                if eslesir(b, hedef.read_text(encoding="utf-8").split("\n---\n", 1)[-1]):
                    rapor.append((b["id"], url, "sayfa metni"))
                    return True
                hedef.unlink()
        rapor.append((b["id"], url, "sayfada tam metin yok"))
        return False
    rapor.append((b["id"], url, f"desteklenmeyen biçim: {tip}"))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arastirma", default=str(KOK.parent / "arastirma"))
    a = ap.parse_args()
    belgeler = belgeleri_oku()
    tum = {}
    for b in belgeler.values():
        tum[b["id"]] = b
        for _, eski in b.get("eski_kimlikler", []):
            tum.setdefault(eski, b)
    segmentler = {s["id"]: s for s in (json.loads(SEGMENT.read_text(encoding="utf-8")) if SEGMENT.exists() else [])}
    atla_dosya = Path(a.arastirma) / "atla.json"
    atla = set(json.loads(atla_dosya.read_text(encoding="utf-8"))) if atla_dosya.exists() else set()
    rapor = []
    biten = set()
    for dosya in sorted(Path(a.arastirma).glob("sonuc*.json")):
        try:
            kayitlar = json.loads(dosya.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("okunamadı:", dosya)
            continue
        for k in kayitlar:
            b = tum.get(k.get("id"))
            if not b or b["tam_metin"] or b["id"] in segmentler or b["id"] in atla or b["id"] in biten:
                continue
            for url in (k.get("url"), k.get("yedek_url")):
                if url and url.startswith("http") and isle(b, url, segmentler, rapor, zorla=k.get("zorla", False),
                                                           baslik=k.get("baslik")):
                    biten.add(b["id"])
                    break
    SEGMENT.write_text(json.dumps(list(segmentler.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for r in rapor:
        print(" | ".join(r))
    print(len(segmentler), "PDF segmenti;", sum(1 for r in rapor if r[2] in ("Word metni", "sayfa metni", "Resmî Gazete metni")), "doğrudan metin")


if __name__ == "__main__":
    main()
