#!/usr/bin/env python3
"""Tam metni olmayan künye kayıtlarını Resmî Gazete'den tamamlar.

Resmî Gazete tarihi bilinen her kayıt için o günün fihristini açar, başlığı
eşleştirir ve metni (HTML ise doğrudan, PDF ise kaynak-isleme/indirilen/rg/
altına indirip segment olarak) alır. Kayıt kimliği korunur.
Not: Bu ilk yayımlanan metindir; sonraki değişiklikler işlenmemiş olabilir.
mevzuat.gov.tr'deki güncel metin (araclar/mevzuat_gov_aktar.py) varsa o önceliklidir.

Kullanım: python araclar/resmi_gazete_aktar.py
"""
import html, json, re, sys, time, unicodedata, urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import belgeleri_oku, sade  # noqa: E402
from mevzuat_gov_aktar import html_md  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (CanliSaglikMevzuati)"}
KAYIT = KOK / "kaynak-isleme" / "resmi-gazete" / "eslesme.json"
PDF_KLASOR = KOK / "kaynak-isleme" / "indirilen" / "rg"
SEGMENT = KOK / "kaynak-isleme" / "segmentler" / "resmi-gazete.json"


def getir(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception:
            if i == 2:
                raise
            time.sleep(4 * (i + 1))


def coz(ham):
    for kod in ("utf-8", "windows-1254"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            pass
    return ham.decode("utf-8", "replace")


def anahtar(s):
    s = re.sub(r"\(.*?\)", " ", s or "")
    return sade(s)


def fihrist_baglari(tarih):
    y, a, g = tarih.split("-")
    url = f"https://www.resmigazete.gov.tr/eskiler/{y}/{a}/{y}{a}{g}.htm"
    sayfa = coz(getir(url))
    sonuc = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', sayfa):
        metin = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split()).strip("–- \xa0")
        if len(metin) > 8:
            sonuc.append((urllib.request.urljoin(url, m.group(1)), metin))
    return sonuc


def main():
    eslesme = json.loads(KAYIT.read_text(encoding="utf-8")) if KAYIT.exists() else {}
    belgeler = belgeleri_oku()
    hedefler = [b for b in belgeler.values() if not b["tam_metin"] and re.match(r"\d{4}-\d{2}-\d{2}$", b.get("rg_tarih") or "")]
    print(len(hedefler), "Resmî Gazete tarihi olan künye kaydı", flush=True)
    segmentler = json.loads(SEGMENT.read_text(encoding="utf-8")) if SEGMENT.exists() else []
    seg_id = {s["id"] for s in segmentler}
    fihrist_onbellek, yazilan = {}, 0
    for i, b in enumerate(hedefler):
        if b["id"] in eslesme and not eslesme[b["id"]]:
            continue
        t = b["rg_tarih"]
        try:
            if t not in fihrist_onbellek:
                fihrist_onbellek[t] = fihrist_baglari(t)
                time.sleep(0.5)
        except Exception as hata:
            print("  ! fihrist alınamadı:", t, hata, flush=True)
            continue
        hedef = anahtar(b["baslik"])
        bul = None
        for url, metin in fihrist_onbellek[t]:
            a = anahtar(metin)
            if a and (a == hedef or (len(hedef) > 15 and (hedef in a or a in hedef))):
                bul = url
                break
        eslesme[b["id"]] = bul or ""
        KAYIT.parent.mkdir(parents=True, exist_ok=True)
        KAYIT.write_text(json.dumps(eslesme, ensure_ascii=False, indent=1), encoding="utf-8")
        if not bul:
            continue
        veri = {k: b.get(k) for k in ("id", "baslik", "tur", "tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu", "etiketler", "not", "durum")}
        veri.update(kaynak="Resmî Gazete (ilk yayımlanan metin; sonraki değişiklikler işlenmemiş olabilir)", kaynak_url=bul)
        veri = {k: v for k, v in veri.items() if v not in (None, "", [])}
        try:
            ham = getir(bul)
        except Exception as hata:
            print("  ! metin alınamadı:", b["baslik"][:50], hata, flush=True)
            continue
        if ham[:4] == b"%PDF":
            PDF_KLASOR.mkdir(parents=True, exist_ok=True)
            ad = re.sub(r"[^0-9a-zA-Z.-]", "_", bul.rsplit("/", 1)[-1])
            (PDF_KLASOR / ad).write_bytes(ham)
            import pdfplumber
            with pdfplumber.open(PDF_KLASOR / ad) as p:
                n = len(p.pages)
            if b["id"] not in seg_id:
                segmentler.append({**veri, "kaynak_pdf": f"rg/{ad}", "pdf_baslangic": 1, "pdf_bitis": n})
                seg_id.add(b["id"])
            yazilan += 1
            continue
        govde = html_md(coz(ham))
        if len(govde) < 400:
            continue
        on = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in veri.items()] + ["---"]
        yol = KOK / "icerik" / b["tur"] / f"{b['id']}.md"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text("\n".join(on) + "\n\n" + govde, encoding="utf-8")
        yazilan += 1
        if yazilan % 10 == 0:
            print(f"  {yazilan} tam metin ({i + 1}/{len(hedefler)})", flush=True)
    SEGMENT.write_text(json.dumps(segmentler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{yazilan} kayıt tamamlandı; {sum(1 for v in eslesme.values() if not v)} kayıt fihristte bulunamadı")


if __name__ == "__main__":
    main()

