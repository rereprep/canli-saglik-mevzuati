#!/usr/bin/env python3
"""Kaynak belgelerdeki koyu/italik biçimi sitedeki metinlere aktarır.

Metin yeniden aktarılmaz; kaynaktaki koyu/italik parçalar sitedeki metinde sırasıyla aranır ve
yalnız birebir (boşluklardan bağımsız) eşleşen yerler **koyu** / <i>italik</i> ile işaretlenir.

Kullanım:
  python3 araclar/bicim_aktar.py --indir [--sinir N] [--id ...]   # kaynakları önbelleğe al
  python3 araclar/bicim_aktar.py --uygula [--yaz] [--id ...]      # eşleştir (önizleme / yaz)
"""
import argparse, html, json, re, ssl, sys, time, unicodedata, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
ONB = KOK.parent / "arastirma" / "bicim-kaynak"
RAPOR = KOK.parent / "arastirma" / "bicim-rapor.json"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
BLOK = {"p", "div", "br", "td", "th", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "center", "blockquote"}
BOS = {"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "wbr", "o:p"}


def on_bilgi(md):
    s = md.read_text(encoding="utf-8")
    if not s.startswith("---\n") or "\n---\n" not in s[4:]:
        return None, None, s
    i = s.index("\n---\n", 4)
    h = s[:i]; b = s[i + 5:]
    v = {}
    for l in h.splitlines()[1:]:
        m = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', l)
        if m: v[m.group(1)] = m.group(2)
    return v, s[:i + 5], b


def kaynak_turu(v):
    u = v.get("kaynak_url", "")
    if v.get("ocr") == "true" or not u or ".gov.tr" not in u:
        return None
    if "mevzuat.gov.tr/mevzuat?" in u:
        return "mevzuat"
    if u.lower().split("?")[0].endswith(".pdf"):
        return "pdf"
    if u.lower().split("?")[0].endswith((".docx",)):
        return "docx"
    if "resmigazete.gov.tr" in u:
        return "rg"
    if "saglik.gov.tr" in u:
        return "sayfa"
    return "sayfa"


def al(u, deneme=3):
    q = urllib.request.Request(u.replace(" ", "%20"), headers={"User-Agent": "Mozilla/5.0"})
    for d in range(deneme):
        try:
            return urllib.request.urlopen(q, timeout=45, context=ctx).read()
        except Exception as e:
            if d == deneme - 1: raise
            time.sleep(2 + 3 * d)


def indir(v, kimlik):
    tur = kaynak_turu(v); u = v["kaynak_url"]
    if tur == "mevzuat":
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(u).query))
        u = (f"https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur={q.get('MevzuatTur')}"
             f"&MevzuatNo={q.get('MevzuatNo')}&MevzuatTertip={q.get('MevzuatTertip', '5')}")
    uz = {"pdf": "pdf", "docx": "docx"}.get(tur, "html")
    hedef = ONB / f"{kimlik}.{uz}"
    if hedef.exists() and hedef.stat().st_size > 500:
        return hedef
    veri = al(u)
    if tur in ("sayfa", "rg") and b"%PDF" not in veri[:1024]:
        sayfa = veri.decode("utf-8", "ignore")
        bag = re.findall(r'href="([^"]+\.(?:pdf|docx))"', sayfa, re.I)
        bag = [x for x in bag if not re.search(r"cerez|çerez|kvkk|kisisel|kişisel|politika|aydinlatma|aydınlatma", x, re.I)]
        if tur == "sayfa" and bag:
            l = html.unescape(bag[0])
            l = urllib.parse.urljoin(u, l)
            veri = al(l)
            hedef = ONB / f"{kimlik}.{'docx' if l.lower().endswith('docx') else 'pdf'}"
    hedef.write_bytes(veri)
    return hedef


def stil_siniflari(s):
    """<style> bloklarındaki sınıf kurallarından koyu/italik sınıfları çıkarır."""
    koyu, italik = set(), set()
    for blok in re.findall(r"(?is)<style[^>]*>(.*?)</style>", s):
        blok = re.sub(r"(?s)/\*.*?\*/", "", blok).replace("<!--", "").replace("-->", "")
        for sec, govde in re.findall(r"([^{}]+)\{([^}]*)\}", blok):
            g = govde.lower().replace(" ", "").replace("\n", "")
            ad = set(re.findall(r"\.([\w-]+)", sec))
            if re.search(r"font-weight:(bold|[6-9]00)", g): koyu |= ad
            if "font-style:italic" in g: italik |= ad
    return koyu, italik


class Ayristir(HTMLParser):
    def __init__(self, koyu_sinif=(), italik_sinif=()):
        super().__init__(convert_charrefs=True)
        self.yigin = [("kok", False, False)]; self.parca = []; self.atla = 0
        self.ks = set(koyu_sinif); self.is_ = set(italik_sinif)

    def durum(self):
        return self.yigin[-1][1], self.yigin[-1][2]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ("script", "style", "head", "title"):
            self.atla += 1; return
        if tag in BLOK:
            self.parca.append(("\x00", False, False))
        if tag in BOS:
            return
        k, i = self.durum()
        st = (dict(attrs).get("style") or "").lower().replace(" ", "")
        if tag in ("b", "strong") or re.search(r"font-weight:(bold|[6-9]00)", st): k = True
        if re.search(r"font-weight:(normal|[1-4]00)", st): k = False
        sinif = set((dict(attrs).get("class") or "").split())
        if sinif & self.ks: k = True
        if sinif & self.is_: i = True
        if tag in ("i", "em") or "font-style:italic" in st: i = True
        if "font-style:normal" in st: i = False
        if tag in ("h1", "h2", "h3", "h4", "th"): k = k  # başlıklar zaten koyu gösterilir
        self.yigin.append((tag, k, i))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "head", "title"):
            self.atla = max(0, self.atla - 1); return
        if tag in BLOK:
            self.parca.append(("\x00", False, False))
        for j in range(len(self.yigin) - 1, 0, -1):
            if self.yigin[j][0] == tag:
                del self.yigin[j:]; break

    def handle_data(self, d):
        if self.atla: return
        k, i = self.durum()
        self.parca.append((d.replace("\n", " ").replace("\r", " ").replace("\xa0", " "), k, i))


def html_parcalar(yol):
    ham = yol.read_bytes()
    m = re.search(rb'charset=["\']?([\w-]+)', ham[:3000])
    kod = (m.group(1).decode() if m else "utf-8").lower()
    if kod in ("windows-1254", "iso-8859-9"): kod = "cp1254"
    try:
        s = ham.decode("utf-8")
    except UnicodeDecodeError:
        try: s = ham.decode(kod, "replace")
        except LookupError: s = ham.decode("cp1254", "replace")
    a = Ayristir(*stil_siniflari(s)); a.feed(s)
    return a.parca


def pdf_parcalar(yol):
    import pdfplumber, logging
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    out = []
    with pdfplumber.open(yol) as pdf:
        for pg in pdf.pages:
            pg = pg.filter(lambda o: o.get("object_type") != "char" or (abs(o["matrix"][1]) < 0.01 and abs(o["matrix"][2]) < 0.01))
            onc_top = None
            for w in pg.extract_words(x_tolerance=1.5, extra_attrs=["fontname"], keep_blank_chars=False):
                if not w.get("upright", True): continue
                if onc_top is not None and abs(w["top"] - onc_top) > 3: out.append(("\x00", False, False))
                onc_top = w["top"]
                fn = w["fontname"].split("+")[-1]
                k = bool(re.search(r"bold|black|heavy|semibold|demi|,B$|-B$|BD$", fn, re.I))
                i = bool(re.search(r"italic|oblique|-It$|,I$|-BI$|BoldIt|,BI$", fn, re.I))
                out.append((w["text"] + " ", k, i))
            out.append(("\x00", False, False))
    return out


def docx_parcalar(yol):
    from docx import Document
    out = []
    for p in Document(str(yol)).paragraphs:
        for r in p.runs:
            out.append((r.text, bool(r.bold), bool(r.italic)))
        out.append(("\x00", False, False))
    return out


def bicimli_kosular(parcalar):
    """Ardışık aynı biçimli parçaları birleştirip yalnız koyu/italik koşuları döndürür (paragraf sınırında böler)."""
    kos, cur = [], None
    for t, k, i in parcalar:
        for j, satir in enumerate(t.split("\x00")):
            if j > 0:
                if cur: kos.append(cur); cur = None
            if not satir: continue
            if cur and cur[1] == k and cur[2] == i:
                cur[0] += satir
            elif cur and not re.search(r"\w", satir) and len(satir.strip()) <= 3:
                cur[0] += satir
            else:
                if cur: kos.append(cur)
                cur = [satir, k, i]
    if cur: kos.append(cur)
    return [(" ".join(t.split()), k, i) for t, k, i in kos if (k or i) and len(re.sub(r"\W", "", t)) >= 3]


def norm(c):
    return unicodedata.normalize("NFC", c)


def sikistir(b):
    """Gövdeyi işaretlerden ve boşluklardan arındırılmış dizgeye çevirir; her karakter için gövde konumunu tutar."""
    harf, konum = [], []
    i = 0
    while i < len(b):
        if b.startswith("**", i): i += 2; continue
        if b.startswith("<i>", i): i += 3; continue
        if b.startswith("</i>", i): i += 4; continue
        c = b[i]
        if not c.isspace():
            harf.append(c); konum.append(i)
        i += 1
    return "".join(harf), konum


def isaretli_mi(b, bas, son):
    """Bölge zaten koyu ise (paragraf içinde açık ** varsa) True."""
    p0 = b.rfind("\n\n", 0, bas) + 1
    return b[p0:bas].count("**") % 2 == 1


def uygula(b, kosular):
    sik, konum = sikistir(b)
    imler = []  # (bas, son, koyu, italik)
    imlec = 0; bulunan = 0
    for t, k, i in kosular:
        igne = re.sub(r"\s", "", norm(t))
        if len(igne) < 3: continue
        def sinirda(j):
            bas = konum[j]; son = konum[j + len(igne) - 1] + 1
            once = b[bas - 1] if bas > 0 else " "; sonra = b[son] if son < len(b) else " "
            return not (once.isalnum() and igne[0].isalnum()) and not (sonra.isalnum() and igne[-1].isalnum())
        j = sik.find(igne, imlec)
        while j >= 0 and not sinirda(j):
            j = sik.find(igne, j + 1)
        if j < 0:
            adaylar = [m.start() for m in re.finditer(re.escape(igne), sik)]
            adaylar = [x for x in adaylar if sinirda(x)]
            if len(adaylar) == 1: j = adaylar[0]
            else: continue
        bas = konum[j]; son = konum[j + len(igne) - 1] + 1
        imlec = j + len(igne)
        satir_bas = b.rfind("\n", 0, bas) + 1
        if b[satir_bas:satir_bas + 1] in "#|":  # başlık / tablo satırları
            continue
        if k and (isaretli_mi(b, bas, son) or "**" in b[bas:son]): k = False
        p0 = b.rfind("\n\n", 0, bas) + 1
        if "<i>" in b[bas:son] or "</i>" in b[bas:son] or b[p0:bas].count("<i>") > b[p0:bas].count("</i>"): i = False
        if not (k or i): continue
        imler.append((bas, son, k, i)); bulunan += 1
    if not imler: return b, 0
    # çakışanları ele: uzun bölge öncelikli
    temiz = []
    for m in sorted(imler, key=lambda m: -(m[1] - m[0])):
        if any(m[0] < t[1] and t[0] < m[1] for t in temiz): continue
        temiz.append(m)
    temiz.sort()
    out = []; onc = 0
    for bas, son, k, i in temiz:
        out.append(b[onc:bas])
        parca = b[bas:son]
        satirlar = parca.split("\n")
        yeni = []
        for s in satirlar:
            if not s.strip(): yeni.append(s); continue
            l = len(s) - len(s.lstrip()); r = len(s.rstrip())
            ic = s[l:r]
            if i: ic = f"<i>{ic}</i>"
            if k: ic = f"**{ic}**"
            yeni.append(s[:l] + ic + s[r:])
        out.append("\n".join(yeni)); onc = son
    out.append(b[onc:])
    sonuc = re.sub(r"(?<=\S)\*\*([ \t]+)\*\*(?=\S)", r"\1", "".join(out))
    return sonuc, len(temiz)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", action="store_true"); ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--yaz", action="store_true"); ap.add_argument("--id", nargs="*"); ap.add_argument("--tur", nargs="*")
    ap.add_argument("--sinir", type=int, default=0); ap.add_argument("--goster", action="store_true")
    a = ap.parse_args()
    ONB.mkdir(parents=True, exist_ok=True)
    rapor = json.loads(RAPOR.read_text()) if RAPOR.exists() else {}
    say = 0
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        if a.id and not any(md.stem.startswith(x) for x in a.id): continue
        v, h, b = on_bilgi(md)
        if not v or len(b.strip()) < 200: continue
        tur = kaynak_turu(v)
        if not tur or (a.tur and tur not in a.tur): continue
        if a.sinir and say >= a.sinir: break
        say += 1
        r = rapor.setdefault(md.stem, {"tur": tur})
        try:
            if a.indir:
                if not any((ONB / f"{md.stem}.{u}").exists() for u in ("html", "pdf", "docx")):
                    indir(v, md.stem); time.sleep(0.6)
                r["indi"] = True
            if a.uygula:
                yol = next((ONB / f"{md.stem}.{u}" for u in ("html", "pdf", "docx") if (ONB / f"{md.stem}.{u}").exists()), None)
                if not yol: r["durum"] = "kaynak yok"; continue
                if b"%PDF" in yol.read_bytes()[:1024]: P = pdf_parcalar(yol)
                elif yol.suffix == ".docx": P = docx_parcalar(yol)
                else: P = html_parcalar(yol)
                kos = bicimli_kosular(P)
                toplam = sum(len(t) for t, _, _ in kos); govde = len(b)
                if govde and toplam > 0.6 * govde:
                    r.update(durum="çok fazla biçim, atlandı", kosu=len(kos)); continue
                yeni, n = uygula(b, kos)
                r.update(durum="ok", kosu=len(kos), eslesen=n)
                if a.goster:
                    print("##", md.stem, tur, "koşu", len(kos), "eşleşen", n)
                    for t, k, i in kos[:12]: print("   ", "K" if k else " ", "İ" if i else " ", t[:90])
                if a.yaz and n:
                    md.write_text(h + yeni, encoding="utf-8")
        except Exception as e:
            r["hata"] = str(e)[:120]
    RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=0))
    from collections import Counter
    c = Counter((x.get("tur"), x.get("durum", "-")) for x in rapor.values())
    print(say, "belge;", dict(c))
    print("eşleşen toplam:", sum(x.get("eslesen", 0) for x in rapor.values()), "hata:", sum(1 for x in rapor.values() if "hata" in x))


if __name__ == "__main__":
    main()

