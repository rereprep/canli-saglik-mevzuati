#!/usr/bin/env python3
"""RG'de yalnız taranmış PDF olarak bulunan ilk metinler: Tesseract çıktısını (sayfa başına .txt) paragraflara çevirir,
değişiklik notu taşımayan maddelerde OCR paragrafını güncel metindeki karşılığıyla değiştirir (okuma hatalarını giderir),
kalan paragrafları denetim için listeler.
Kullanım: python araclar/ocr_ilk_metin.py <kimlik> <txt_klasörü> [ilk_sayfa son_sayfa]
Çıktı: kaynak-isleme/surum/ocr/<kimlik>.md ve <kimlik>.denetim.json"""
import difflib, json, re, sys
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
import surum_olustur as so  # noqa: E402

BAS = re.compile(r"^\s*(?:(?:GEÇİCİ|Geçici|EK|Ek)\s+)?(?:MADDE|Madde)\s*\d+|^\s*[a-zçğıöşü]{1,2}\)\s|^\s*\(\d+\)\s|^\s*\d+\)\s")
UST = re.compile(r"Sayfa\s*[:.]?\s*\d+|RESM[İI]\s*GAZETE|Sayı\s*[:.]\s*\d{5}")
NOT = re.compile(r"\((?:Değişik|Ek|Mülga|İptal|Yeniden düzenleme|Değişiklik)[^()]*\)")
SAYFA_NO = re.compile(r"^\s*\d{1,3}\s*$")


def paragraflar(metinler):
    out = []
    for s in metinler:
        satirlar = s.split("\n")
        for i in range(min(3, len(satirlar))):
            if UST.search(satirlar[i]):
                satirlar[i] = ""
        blok = []
        for sat in satirlar + [""]:
            sat = sat.strip()
            if not sat or SAYFA_NO.match(sat):
                if blok:
                    out.append(blok)
                    blok = []
                continue
            if blok and BAS.match(sat):
                out.append(blok)
                blok = []
            blok.append(sat)
    par = []
    for blok in out:
        metin = ""
        for sat in blok:
            if metin.endswith("-") and sat[:1].islower():
                metin = metin[:-1] + sat
            else:
                metin = (metin + " " + sat).strip()
        par.append(metin)
    birlesik = []
    for p in par:
        if birlesik and p[:1].islower() and not BAS.match(p) and not re.search(r"[.:;]$", birlesik[-1]):
            birlesik[-1] += " " + p
        else:
            birlesik.append(p)
    return birlesik


def guncel_maddeler(dosya):
    b = so.Belge(so.govde_al(dosya))
    out = {}
    for k, i, j in b.maddeler():
        pars = [p.replace("**", "") for p in b.p[i:j]]
        # madde başında not varsa (bütün madde değişmiş) hiçbir paragrafı eşlenmez; yoksa yalnız notsuz paragraflar
        bas_not = bool(NOT.search(pars[0][:160])) if pars else False
        out[k] = ([] if bas_not else [p for p in pars if not NOT.search(p)], bas_not)
    return out


def main():
    kimlik, klasor = sys.argv[1], Path(sys.argv[2])
    dosyalar = sorted(klasor.glob("p*.txt"))
    if len(sys.argv) > 4:
        a, z = int(sys.argv[3]), int(sys.argv[4])
        dosyalar = [f for f in dosyalar if a <= int(f.stem[1:]) <= z]
    par = paragraflar([f.read_text() for f in dosyalar])
    md_yol = next((KOK / "icerik").glob(f"*/{kimlik}.md"))
    baslik = re.search(r'^baslik: "([^"]+)"', md_yol.read_text(encoding="utf-8"), re.M).group(1)
    par = so.paragraflar(so.ilk_metni_kirp("\n\n".join(par), baslik))
    # son: yürütme maddesinden sonrası (imza, ekler, sonraki mevzuat) atılır
    for x, p in enumerate(par):
        if BAS.match(p) and re.search(r"hükümlerini\s.{0,80}yürütür", p):
            par = par[: x + 1]
            break
        if x > 20 and re.fullmatch(r"(?:EK|Ek)\s*[-–]?\s*(?:1|I|l)", p.strip()):
            par = par[:x]
            break
    gun = guncel_maddeler(md_yol)
    belge = so.Belge("\n\n".join(par))
    yeni, denetim, eslesen = list(belge.p), [], 0
    for k, i, j in belge.maddeler():
        g = gun.get(k)
        for x in range(i, j):
            p = belge.p[x]
            if g and g[0]:
                ad = max(g[0], key=lambda c: difflib.SequenceMatcher(None, p, c, autojunk=False).ratio())
                if difflib.SequenceMatcher(None, p, ad, autojunk=False).ratio() >= 0.85:
                    yeni[x] = ad
                    eslesen += 1
                    continue
            denetim.append({"i": x, "madde": k, "metin": p})
    cikti = KOK / "kaynak-isleme" / "surum" / "ocr"
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / f"{kimlik}.md").write_text("\n\n".join(yeni) + "\n", encoding="utf-8")
    (cikti / f"{kimlik}.denetim.json").write_text(json.dumps(denetim, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{kimlik}: {len(belge.maddeler())} madde, {eslesen} paragraf güncel metinle eşlendi, {len(denetim)} paragraf denetlenecek")


if __name__ == "__main__":
    main()
