#!/usr/bin/env python3
"""HSGM mevzuat sayfasındaki (hsgm.saglik.gov.tr/tr/mevzuat.html) belgeleri indirir ve icerik/ altına yazar.
Girdi: ../arastirma/hsgm/liste.json (sayfadaki 'publications' dizisinden sitede olmayanlar)
Metin katmanı olan PDF'ler doğrudan aktarılır (künyede otomatik: true); taranmış olanlar
../arastirma/hsgm/taranmis.json'a yazılır (ajanlar görüntüden aktarır).
"""
import json, re, subprocess, sys, unicodedata, html
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import sade  # noqa
from kitaptan_cikar import on_bilgi  # noqa
from mevzuat_gov_aktar import Istemci, html_md  # noqa

ARS = KOK.parent / "arastirma" / "hsgm"
PDF = ARS / "pdf"; PDF.mkdir(parents=True, exist_ok=True)
TUR = {"Genel Nitelikli Yazı ve Görüşler": "yazi", "Genelgeler": "genelge", "Yönetmelikler": "yonetmelik",
       "Tebliğler": "teblig", "Kanunlar": "kanun", "Yönergeler": "yonerge", "Usul ve Esaslar": "yonerge",
       "Tüzükler": "tuzuk", "Bakanlar Kurulu Kararları": "bkk"}


def tur_bul(x):
    t, b = TUR[x["category"]], x["title"]
    if "Kanun Hükmünde Kararname" in b and not re.search(r"Hakkında Kanun\b", b): return "khk"
    if t == "tuzuk" and "Yönetmelik" in b: return "yonetmelik"
    if "İzlem Formu" in b: return "yazi"
    return t


def harf_onar(s):
    """PDF yazı tipinde boşluk yerine kullanılan sedil işaretini (ţ, ļ, Ķ, ı̧ ...) boşluğa çevirir."""
    s = unicodedata.normalize("NFD", s)
    out = []
    for ch in s:
        if ch == "\u0327":
            onceki = out[-1] if out else ""
            if onceki in "cCsS":
                out.append(ch)
            else:
                out.append(" ")
            continue
        out.append(ch)
    s = unicodedata.normalize("NFC", "".join(out))
    return re.sub(r"[ \t]{2,}", " ", s)


AT = re.compile(r"(?i)^(bu belge,? güvenli elektronik imza|belge doğrulama|evrakı doğrulamak|adres\s*:|telefon\s*no|e-posta|kep adresi|internet adresi|bilgi için|\d{2}\.\d{2}\.\d{4} \d\d:\d\d:\d\d\b)")


def paragrafla(satirlar):
    out = []
    for s in satirlar:
        s = s.strip()
        if not s:
            out.append(""); continue
        if out and out[-1] and not re.search(r"[.:;!?)]$", out[-1]) and re.match(r"[a-zçğıöşü0-9(“\"]", s) \
                and len(out[-1]) > 60:
            out[-1] += " " + s
        else:
            out.append(s)
    return "\n\n".join(x for x in out if x)


def pdf_metni(yol):
    import pdfplumber
    sayfalar = []
    with pdfplumber.open(yol) as p:
        for pg in p.pages:
            sayfalar.append(harf_onar(pg.extract_text(x_tolerance=1.5) or ""))
    return sayfalar


def kunye_cikar(metin, tur, baslik):
    v = {}
    m = re.search(r"Sayı\s*:\s*([^\s].*?)\s+(\d{1,2})[./](\d{1,2})[./]((?:19|20)\d\d)\b", metin[:3000])
    if m:
        v["sayi"] = m[1].strip(" -/")
        v["tarih"] = f"{m[4]}-{int(m[3]):02d}-{int(m[2]):02d}"
    if tur == "genelge":
        g = re.search(r"((?:19|20)\d\d)\s*[/-]\s*(\d{1,3})\b", baslik) or re.search(r"GENELGE\s*\n?\s*((?:19|20)\d\d)\s*/\s*(\d{1,3})", metin[:3000])
        if g: v["sayi"] = f"{g[1]}/{g[2]}"
    return v


def main():
    liste = json.loads((ARS / "liste.json").read_text())
    ist = None; taranan = []; rapor = []
    for x in liste:
        tur = tur_bul(x)
        kid = f"hsgm-{x['id']}-" + sade(x["title"]).replace(" ", "-")[:70].strip("-")
        hedef = KOK / "icerik" / tur / f"{kid}.md"
        if hedef.exists():
            continue
        url = x["url"].strip()
        baslik = " ".join(x["title"].split())
        birim = ", ".join(t["title"] for t in x.get("tags", []))
        govde, ek = "", {}
        try:
            m = re.search(r"MevzuatNo=(\d+)&MevzuatTur=(\d+)&MevzuatTertip=(\d+)", url)
            if m:
                ist = ist or Istemci()
                govde = html_md(ist.metin(int(m[2]), m[1], m[3]))
                kaynak = "Mevzuat Bilgi Sistemi (mevzuat.gov.tr), güncel metin"
            elif url.lower().endswith((".htm", ".html")):
                ham = subprocess.run(["curl", "-sL", "-m", "60", "-A", "Mozilla/5.0", url], capture_output=True).stdout
                try: s = ham.decode("utf-8")
                except UnicodeDecodeError: s = ham.decode("windows-1254", "replace")
                govde = html_md(s); kaynak = "Resmî Gazete (resmigazete.gov.tr)"
            else:
                ext = url.rsplit(".", 1)[-1].lower()[:4]
                yol = PDF / f"{x['id']}.{ext}"
                if not yol.exists() or yol.stat().st_size < 500:
                    subprocess.run(["curl", "-sL", "-m", "90", "-A", "Mozilla/5.0", "-o", str(yol), url.replace(" ", "%20")])
                kaynak = "T.C. Sağlık Bakanlığı Halk Sağlığı Genel Müdürlüğü (hsgm.saglik.gov.tr)"
                if ext == "pdf":
                    sayfalar = pdf_metni(yol)
                    ort = sum(len(s) for s in sayfalar) / max(1, len(sayfalar))
                    if ort < 250:
                        taranan.append({"id": kid, "tur": tur, "baslik": baslik, "url": url, "pdf": str(yol),
                                        "sayfa": len(sayfalar), "birim": birim, "dosya": str(hedef)})
                        govde = None
                    else:
                        satir = [l for s in sayfalar for l in s.splitlines() if not AT.match(l.strip())]
                        govde = paragrafla(satir); ek["otomatik"] = True
                elif ext in ("doc", "docx", "rtf", "odt"):
                    govde = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(yol)], capture_output=True, text=True).stdout
                    govde = paragrafla(govde.splitlines()); ek["otomatik"] = True
                else:
                    govde = ""
        except Exception as e:
            rapor.append((kid, "HATA " + str(e)[:120])); continue
        if govde is None:
            rapor.append((kid, "taranmış")); continue
        if len((govde or "").strip()) < 80:
            rapor.append((kid, f"metin yok ({url.rsplit('.',1)[-1][:5]})")); continue
        v = {"id": kid, "baslik": baslik, "tur": tur, "birim": birim or "Halk Sağlığı Genel Müdürlüğü",
             "kaynak": kaynak, "kaynak_url": url, "durum": "yürürlükte"}
        v.update(kunye_cikar(govde, tur, baslik))
        satirlar = on_bilgi(v).rstrip().split("\n")
        if ek.get("otomatik"):
            satirlar.insert(-1, "otomatik: true")
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text("\n".join(satirlar) + "\n\n" + govde.strip() + "\n", encoding="utf-8")
        rapor.append((kid, "yazıldı " + str(len(govde))))
    (ARS / "taranmis.json").write_text(json.dumps(taranan, ensure_ascii=False, indent=1))
    (ARS / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
    import collections
    print(collections.Counter(r[1].split()[0] for r in rapor), "taranmış:", len(taranan))


if __name__ == "__main__":
    main()

