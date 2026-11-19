#!/usr/bin/env python3
"""RG'den indirilen ilk metne değişiklik metinlerini sırayla uygulayarak tarihli sürümler üretir.
Her sürümün son hâli güncel (mevzuat.gov.tr) metinle madde madde karşılaştırılır; eşleşen maddelerin ara
metinleri doğrulanmış, eşleşmeyenler "kesin değil" sayılır.
Çıktı: kaynak-isleme/surum/<kimlik>.json  Kullanım: python araclar/surum_olustur.py [kimlik ...]"""
import difflib, html, json, re, sys
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from mevzuat_gov_aktar import html_md  # noqa: E402
from surum_indir import getir, coz, sade  # noqa: E402

SIRA = {"birinci": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5, "altıncı": 6, "yedinci": 7, "sekizinci": 8,
        "dokuzuncu": 9, "onuncu": 10}
for _o, _n in list(SIRA.items())[:9]:
    SIRA["on " + _o] = 10 + _n
    SIRA["on" + _o] = 10 + _n
    SIRA["yirmi " + _o] = 20 + _n
SIRA["yirminci"] = 20
SIRA_RE = "|".join(sorted(SIRA, key=len, reverse=True))
MADDE_BAS = re.compile(r"^(?:#+\s*)?\**\s*“?\s*(GEÇİCİ MADDE|Geçici Madde|EK MADDE|Ek Madde|MADDE|Madde)\s*(\d+)\s*(?:/\s*([A-Za-z]))?\s*\.?\s*\**\s*[-–—]")
NOT = re.compile(r"\((?:Değişik|Ek|Mülga|İptal|Yeniden düzenleme|Değişiklik)[^()]*\)")


def madde_anahtari(tur, no, harf=""):
    t = (tur or "").replace("İ", "i").replace("I", "ı").lower()
    on = "gecici-" if "geçici" in t or "geci" in t else "ek-" if t.startswith("ek") else ""
    return on + str(int(no)) + (harf or "").lower()


def paragraflar(md):
    return [p.strip() for p in re.split(r"\n{2,}", md) if p.strip()]


def temiz_p(p):
    return re.sub(r"^#{2,4}\s+", "", p.strip())


class Belge:
    def __init__(self, md):
        self.p = [temiz_p(x) for x in paragraflar(md)]

    def maddeler(self):
        """[(anahtar, baslangic, bitis)]; madde başlığı (önceki kısa satır) maddeye dahil değildir."""
        bas = []
        for i, p in enumerate(self.p):
            m = MADDE_BAS.match(p.replace("**", ""))
            if m:
                bas.append((madde_anahtari(m.group(1), m.group(2), m.group(3)), i))
        out = []
        for j, (k, i) in enumerate(bas):
            son = bas[j + 1][1] if j + 1 < len(bas) else len(self.p)
            # bir sonraki maddenin başlığı ve bölüm başlıkları bu maddeye ait değil
            while son - 1 > i and _baslik_mi(self.p[son - 1]):
                son -= 1
            out.append((k, i, son))
        return out

    def madde(self, k):
        for a, i, j in self.maddeler():
            if a == k:
                return i, j
        return None


def _baslik_mi(p):
    d = p.replace("**", "").strip()
    return (len(d) < 90 and not re.search(r"[.;:,]$", d) and not re.match(r"^(\(\d+\)|[a-zçğıöşü]{1,2}\)|\d+[.)])", d)
            and not MADDE_BAS.match(d)) or bool(re.match(r"^[A-ZÇĞİÖŞÜ ]+BÖLÜM|^[A-ZÇĞİÖŞÜ]+ (KISIM|BÖLÜM)", d))


ETIKET = re.compile(r"^(?:\**\s*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+\s*(?:/\s*[A-Za-z])?\s*\.?\s*\**\s*[-–—]\s*\**\s*)?(?:\((?:Değişik|Ek|Mülga)[^()]*\)\s*)*")


def etiket(p):
    """Paragrafın birimi: ('f', 3) fıkra, ('b','a') bent, ('a', 2) alt bent ya da None."""
    d = ETIKET.sub("", p.replace("**", "").lstrip("“\""), count=1).strip()
    m = re.match(r"^\((\d+)\)", d)
    if m:
        return ("f", int(m.group(1)))
    m = re.match(r"^([a-zçğıöşü]{1,2})\)", d)
    if m:
        return ("b", m.group(1))
    m = re.match(r"^(\d+)[)]", d)
    if m:
        return ("a", int(m.group(1)))
    return None


def birimler(par, i, j):
    """Madde aralığındaki fıkra/bent/alt bent birimleri: [(seviye, etiket, basl, bitis, ust_fikra, ust_bent)]."""
    out, fno, bno = [], 0, None
    numarali = any(etiket(par[x]) and etiket(par[x])[0] == "f" for x in range(i, j))
    for x in range(i, j):
        e = etiket(par[x])
        if e and e[0] == "f" or (not numarali and not e and not (x > i and _baslik_mi(par[x]))):
            fno = e[1] if e else fno + 1
            out.append(["f", fno, x, None, fno, None])
            bno = None
        elif e and e[0] == "b":
            bno = e[1]
            out.append(["b", bno, x, None, fno, bno])
        elif e and e[0] == "a":
            out.append(["a", e[1], x, None, fno, bno])
    sev = {"f": 0, "b": 1, "a": 2}
    for n, u in enumerate(out):
        son = j
        for v in out[n + 1:]:
            if sev[v[0]] <= sev[u[0]]:
                son = v[2]
                break
        u[3] = son
    return out


# ---------------------------------------------------------------- değişiklik metni çözümleme
def degisiklik_maddeleri(md):
    """[(talimat, [yuk paragrafları])] — 'Bu Yönetmelik yayımı tarihinde yürürlüğe girer' gibi maddeler dahil."""
    par = [temiz_p(x) for x in paragraflar(md)]
    out, tirnak = [], 0
    for p in par:
        d = p.replace("**", "")
        mb = re.match(r"^(MADDE|Madde)\s*(\d+)\s*\.?\s*[-–—]", d)
        # Yalnız başlıkla birlikte değiştirilen ve tırnaklı başlığın hemen
        # ardından gelen hedef madde, değişiklik kanununun maddesi değildir.
        yuk_madde = (mb and tirnak and out and len(out[-1][1]) == 1
                     and "başlığı ile birlikte" in out[-1][0].lower()
                     and hedef_madde(out[-1][0], None) == str(int(mb.group(2))))
        if mb and not yuk_madde:
            tirnak = 0
            out.append([re.sub(r"^(MADDE|Madde)\s*\d+\s*\.?\s*[-–—]\s*", "", d), [], int(re.match(r"^(?:MADDE|Madde)\s*(\d+)", d).group(1))])
        elif out:
            # eski RG metinlerinde düz tırnak: "…" → “…”
            if re.match(r'^\**\s*"', p):
                p = re.sub(r'^(\**\s*)"', r"\1“", p)
                p = re.sub(r'"(\s*(?:\**)?\s*)$', r"”\1", p)
            out[-1][1].append(p)
            if tirnak or re.match(r"^\**\s*“", p):
                tirnak = max(0, tirnak + p.count("“") - p.count("”"))
    return out


def yuk_birimleri(yuk):
    """Tırnaklı yük paragraflarını temizler: baştaki “ ve sondaki ” atılır."""
    out = []
    for p in yuk:
        q = p.strip()
        q = re.sub(r"^(\**)“", r"\1", q)
        q = re.sub(r"”(\**)\s*$", r"\1", q)
        q = re.sub(r"”\s*$", "", q)
        out.append(q.strip())
    return [q for q in out if q]


def hedef_madde(t, onceki):
    m = re.search(r"(?:(geçici|ek)\s+)?(\d+)\s*(?:/\s*([A-Za-z]))?\s*(?:'|’)?\s*(?:inci|nci|ncı|ıncı|üncü|uncu|ncü|nıcı)?\s*maddes", t, re.I)
    if m:
        return madde_anahtari(m.group(1) or "", m.group(2), m.group(3))
    if re.search(r"aynı maddenin", t, re.I):
        return onceki
    return None


def fikra_no(s, bl=None):
    if bl is not None and re.search(r"\bson\s*fıkra", s) and not re.search(r"(" + SIRA_RE + r")\s*fıkra", s):
        return max((u[1] for u in bl if u[0] == "f"), default=None)
    m = re.search(r"\((\d+)\)\s*numaralı\s*fıkra", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(" + SIRA_RE + r")\s*fıkra", s)
    return SIRA[m.group(1)] if m else None


def uygula(belge, talimat, yuk, kunye, onceki_madde, adim):
    """Bir değişiklik maddesini uygular. Dönen: (başarılı mı, etkilenen madde anahtarları, madde bağlamı)."""
    t = " ".join(talimat.split())
    not_ = f"(Değişik:RG-{kunye})"
    par = belge.p
    k = hedef_madde(t, onceki_madde)
    yuk = yuk_birimleri(yuk)
    # ---- ibare işlemleri
    ibareler = re.findall(r"“([^”]+)”\s*(?:ibare|ifade|kelime|sözcük|rakam)(?:si|leri|ı|i|leri)\s*“([^”]*)”\s*şeklinde", t)
    ekle_ib = re.findall(r"“([^”]+)”\s*ibaresinden\s*(?:önce|sonra)\s*gelmek üzere\s*“([^”]+)”\s*ibaresi", t)
    sil_ib = re.findall(r"“([^”]+)”\s*(?:ibare|ifade|kelime|sözcük|rakam)(?:si|leri|ı|i|leri)\s*(?:yürürlükten kaldırıl|madde metninden çıkarıl|metinden çıkarıl|çıkarıl)", t)
    if ibareler or ekle_ib or sil_ib:
        if re.search(r"Yönetmeli[kğ]\w*\s+(?:geçen|yer alan)|Tebliğ\w*\s+(?:geçen|yer alan)|metninde geçen", t) and not k:
            alan = [(0, len(par))]
        else:
            if not k:
                return False, [], onceki_madde
            r = belge.madde(k)
            if not r:
                return False, [], k
            alan = [kapsam_daralt(par, r, t)]
        degisti = False
        for a, b in alan:
            for x in range(a, b):
                y = par[x]
                for eski, yeni in ibareler:
                    y = y.replace(eski, yeni)
                for once, ek in ekle_ib:
                    if "önce gelmek" in t:
                        y = y.replace(once, ek + " " + once, 1)
                    else:
                        y = y.replace(once, once + (" " if not ek[:1] in ",;." else "") + ek, 1)
                for s in sil_ib:
                    y = re.sub(r"\s?" + re.escape(s), "", y, count=1)
                if y != par[x]:
                    par[x] = y
                    degisti = True
        return degisti, [k] if k else ["*"], k
    if not k:
        if re.search(r"yürürlüğe girer|yürütür|yürürlükten kaldırılmıştır", t) and not re.search(r"maddes", t):
            return None, [], onceki_madde  # değişiklik yönetmeliğinin kendi hükmü
        return False, [], onceki_madde
    r = belge.madde(k)
    # ---- yeni madde ekleme
    if re.search(r"aşağıdaki\s+(?:geçici\s+|ek\s+)?madde(?:ler)?\s+eklenmiştir|aşağıdaki\s+(?:geçici\s+|ek\s+)?maddeler?\s", t) and re.search(r"eklenmiştir", t) and not re.search(r"maddesine|maddesinin", t):
        yeni = [p for p in yuk]
        anahtarlar = []
        for p in yeni:
            m = MADDE_BAS.match(p.replace("**", ""))
            if m:
                anahtarlar.append(madde_anahtari(m.group(1), m.group(2), m.group(3)))
        if not anahtarlar:
            return False, [], k
        if "sonra gelmek" in t and r:
            yer = r[1]
        else:
            yer = _ek_yeri(belge, anahtarlar[0])
        par[yer:yer] = _not_ekle(yeni, f"(Ek:RG-{kunye})")
        return True, anahtarlar, anahtarlar[-1]
    if not r:
        return False, [], k
    i, j = r
    # ---- madde tümüyle
    madde_duzey = not re.search(r"fıkra|bend|bent|cümle|paragraf|başlığı\b(?!\s*ile)", t.split("maddes", 1)[1] if "maddes" in t else t)
    if madde_duzey and re.search(r"değiştirilmiştir", t) and yuk:
        bas = 0
        if re.search(r"başlığı ile birlikte", t) and i > 0 and _baslik_mi(par[i - 1]) and not MADDE_BAS.match(yuk[0].replace("**", "")):
            par[i - 1] = yuk[0]
            yuk = yuk[1:]
        par[i:j] = _not_ekle(yuk, not_, madde=True)
        return True, [k], k
    if madde_duzey and re.search(r"yürürlükten kaldırılmıştır", t) and not yuk:
        m = MADDE_BAS.match(par[i].replace("**", ""))
        par[i:j] = [f"**{par[i].replace('**','').split('–')[0].split('-')[0].strip()} –** (Mülga:RG-{kunye})"]
        return True, [k], k
    if re.search(r"başlığı\s+“([^”]+)”\s*şeklinde", t):
        yb = re.search(r"başlığı\s+“([^”]+)”\s*şeklinde", t).group(1)
        if i > 0 and _baslik_mi(par[i - 1]):
            par[i - 1] = yb
            return True, [k], k
        return False, [k], k
    # ---- fıkra / bent / alt bent düzeyi
    bl = birimler(par, i, j)
    f = fikra_no(t, bl)
    bentler = re.findall(r"\(([a-zçğıöşü]{1,2})\)\s*(?:,|ve|bend|bentleri)", t)
    altlar = re.findall(r"\((\d+)\)\s*numaralı\s*alt\s*bent", t)
    if re.search(r"değiştirilmiştir", t) and yuk and not re.search(r"eklenmiş", t):
        gruplar = _yuk_grupla(yuk)
        tamam = True
        for (sev, et), parca in reversed(gruplar):
            if sev == "f":
                hedef = [u for u in bl if u[0] == "f" and u[1] == et]
            elif sev == "b":
                hedef = [u for u in bl if u[0] == "b" and u[1] == et and (f is None or u[4] == f)]
            elif sev == "a":
                b_ = bentler[-1] if bentler else None
                hedef = [u for u in bl if u[0] == "a" and u[1] == et and (f is None or u[4] == f) and (b_ is None or u[5] == b_)]
            else:
                hedef = [u for u in bl if u[0] == "f" and u[1] == (f or 1)] if f else []
            if len(hedef) != 1:
                tamam = False
                continue
            u = hedef[0]
            onek = ""
            if u[2] == i:  # maddenin ilk paragrafı: madde etiketini koru
                m = re.match(r"^(\**\s*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+\s*(?:/\s*[A-Za-z])?\s*\**\s*[-–—]\s*\**\s*)", par[i])
                onek = m.group(1) if m else ""
            yeni = _not_ekle(parca, not_)
            if onek:
                yeni[0] = onek + yeni[0]
            par[u[2]:u[3]] = yeni
        return tamam, [k], k
    if re.search(r"yürürlükten kaldırılmıştır", t) and not yuk:
        hedefler = []
        if altlar:
            hedefler = [u for u in bl if u[0] == "a" and str(u[1]) in altlar and (f is None or u[4] == f) and (not bentler or u[5] in bentler)]
        elif bentler:
            hedefler = [u for u in bl if u[0] == "b" and u[1] in bentler and (f is None or u[4] == f)]
        else:
            nolar = [SIRA[x] for x in re.findall(r"(" + SIRA_RE + r")", t)] + [int(x) for x in re.findall(r"\((\d+)\)\s*numaralı", t)]
            hedefler = [u for u in bl if u[0] == "f" and u[1] in nolar]
        if not hedefler:
            return False, [k], k
        for u in sorted(hedefler, key=lambda u: -u[2]):
            lab = {"f": f"({u[1]})", "b": f"{u[1]})", "a": f"{u[1]})"}[u[0]]
            onek = ""
            if u[2] == i:
                m = re.match(r"^(\**\s*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+\s*\**\s*[-–—]\s*\**\s*)", par[i])
                onek = m.group(1) if m else ""
            par[u[2]:u[3]] = [f"{onek}{lab} (Mülga:RG-{kunye})"]
        return True, [k], k
    if re.search(r"eklenmiştir", t) and yuk and not re.search(r"değiştirilmiş", t):
        gruplar = _yuk_grupla(yuk)
        sev0 = gruplar[0][0][0]
        sonra = re.search(r"(\(\w+\)\s*(?:numaralı\s*)?(?:bendinden|alt bendinden|fıkrasından)|(" + SIRA_RE + r")\s*fıkrasından)\s*sonra", t)
        yer = None
        if sonra:
            s = sonra.group(0)
            if "fıkrasından" in s:
                n = fikra_no(s.replace("fıkrasından", "fıkra"))
                u = [x for x in bl if x[0] == "f" and x[1] == n]
            elif "alt bendinden" in s:
                n = int(re.search(r"\((\d+)\)", s).group(1))
                u = [x for x in bl if x[0] == "a" and x[1] == n and (f is None or x[4] == f)]
            else:
                n = re.search(r"\((\w+)\)", s).group(1)
                u = [x for x in bl if x[0] == "b" and x[1] == n and (f is None or x[4] == f)]
            if len(u) == 1:
                yer = u[0][3]
        elif sev0 == "f":
            yer = j
        elif sev0 == "b":
            u = [x for x in bl if x[0] == "f" and x[1] == (f or 1)]
            yer = u[0][3] if len(u) == 1 else (j if not f else None)
        elif sev0 == "a":
            b_ = bentler[-1] if bentler else None
            u = [x for x in bl if x[0] == "b" and x[1] == b_ and (f is None or x[4] == f)]
            yer = u[0][3] if len(u) == 1 else None
        elif re.search(r"cümle", t):
            u = [x for x in bl if x[0] == "f" and x[1] == (f or 1)]
            if len(u) == 1:
                x = u[0][2]
                par[x] = par[x].rstrip() + f" (Ek cümle:RG-{kunye}) " + " ".join(yuk)
                return True, [k], k
        if yer is None:
            return False, [k], k
        par[yer:yer] = _not_ekle([p for _, ps in gruplar for p in ps], f"(Ek:RG-{kunye})")
        return True, [k], k
    if re.search(r"cümlesi\s+aşağıdaki şekilde değiştirilmiştir", t) and yuk:
        u = [x for x in bl if x[0] == "f" and x[1] == (f or 1)]
        cm = re.search(r"(" + SIRA_RE + r"|son)\s*cümlesi", t)
        if len(u) == 1 and cm:
            x = u[0][2]
            cumleler = re.split(r"(?<=[.])\s+(?=[A-ZÇĞİÖŞÜ(])", par[x])
            n = len(cumleler) if cm.group(1) == "son" else SIRA.get(cm.group(1), 0)
            if 1 <= n <= len(cumleler):
                cumleler[n - 1] = " ".join(yuk)
                par[x] = " ".join(cumleler)
                return True, [k], k
        return False, [k], k
    return False, [k], k


def kapsam_daralt(par, r, t):
    i, j = r
    bl = birimler(par, i, j)
    f = fikra_no(t.split("“")[0], bl)
    b = re.findall(r"\(([a-zçğıöşü]{1,2})\)\s*bend", t.split("“")[0])
    if b:
        u = [x for x in bl if x[0] == "b" and x[1] == b[0] and (f is None or x[4] == f)]
        if len(u) == 1:
            return u[0][2], u[0][3]
    if f:
        u = [x for x in bl if x[0] == "f" and x[1] == f]
        if len(u) == 1:
            return u[0][2], u[0][3]
    return i, j


def _yuk_grupla(yuk):
    """Yük paragraflarını en üst düzey birimlere ayırır: [((seviye, etiket), [paragraflar])]."""
    sev = {"f": 0, "b": 1, "a": 2, None: 3}
    ilk = etiket(yuk[0])
    ust = ilk[0] if ilk else None
    out = []
    for p in yuk:
        e = etiket(p)
        if e and e[0] == ust or not out:
            out.append(((ust, e[1] if e else None), [p]))
        else:
            out[-1][1].append(p)
    return out


def _not_ekle(ps, not_, madde=False):
    ps = list(ps)
    if not ps:
        return ps
    p = ps[0]
    m = re.match(r"^(\**\s*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+\s*(?:/\s*[A-Za-z])?\s*\.?\s*\**\s*[-–—]\s*\**\s*)", p)
    if m:
        ps[0] = m.group(1) + not_ + " " + p[m.end():]
    else:
        m = re.match(r"^(\(\d+\)|[a-zçğıöşü]{1,2}\)|\d+\))\s*", p)
        ps[0] = (m.group(1) + " " + not_ + " " + p[m.end():]) if m else (not_ + " " + p)
    return ps


def _ek_yeri(belge, k):
    md = belge.maddeler()
    if k.startswith("gecici-"):
        g = [x for x in md if x[0].startswith("gecici-")]
        if g:
            return g[-1][2]
    for a, i, j in md:
        if re.search(r"Yürürlük", " ".join(belge.p[max(0, i - 1):i + 1])):
            return i - 1 if i > 0 and _baslik_mi(belge.p[i - 1]) else i
    return md[-1][2] if md else len(belge.p)




# ================================================================ talimat çözümleyici (v2)
_AY = r"(?:\s*,\s*|\s+ve\s+|\s+ile\s+)"
_TOK = re.compile(
    r"(?P<bo>(?P<bon>" + SIRA_RE + r")\s*bölümünün\s*başlığı)"
    r"|(?P<m>(?:(?P<mt>geçici|ek)\s+)?(?P<mliste>(?:\d+\s*(?:['’]?\s*(?:inci|nci|ncı|ıncı|üncü|uncu|ncü))?\s*(?:,\s*|\s+ve\s+|,\s*ve\s+))*)(?P<mn>\d+)\s*(?:/\s*(?P<mh>[A-Za-z])\s*)?['’]?\s*(?:inci|nci|ncı|ıncı|üncü|uncu|ncü|nıcı)?\s*madde(?P<ms>\w*))"
    r"|(?P<am>aynı madde\w*)|(?P<af>aynı fıkra\w*)|(?P<ab>aynı ben[dt]\w*)"
    r"|(?P<f>(?:(?:" + SIRA_RE + r"|son|\(\d+\)\s*numaralı)" + _AY + r")*(?:" + SIRA_RE + r"|son|\(\d+\)\s*numaralı)\s*fıkra(?P<fs>\w*))"
    r"|(?P<a>(?:\(\d+\)(?:\s*numaralı)?" + _AY + r")*\(\d+\)\s*numaralı\s*alt\s*ben[dt](?P<as>\w*))"
    r"|(?P<b>(?:\([a-zçğıöşü]{1,2}\)" + _AY + r")*\([a-zçğıöşü]{1,2}\)\s*ben[dt](?P<bs>\w*))"
    r"|(?P<c>(?P<cl>(?:(?:" + SIRA_RE + r")" + _AY + r")*)(?P<cn>" + SIRA_RE + r"|son)\s*cümle(?P<cs>\w*))"
    r"|(?P<h>başlığı(?!\s*ile))"
    r"|(?P<ib>“[^”]*”)", re.I)


def _ek_tur(ek):
    """Türkçe hal eki: 'g' tamlayan/bulunma (bağlam), 'y' yönelme, 'c' ayrılma, 'n' yalın."""
    e = (ek or "").lower()
    if re.search(r"(n[ıiuü]n|nde|nda|de|da|lerin|ların|lerinde|larında)$", e):
        return "g"
    if re.search(r"(ne|na|ye|ya|e|a)$", e) and not e.endswith(("si", "sı", "leri", "ları", "i", "ı")):
        return "y"
    if re.search(r"(den|dan|nden|ndan)$", e):
        return "c"
    return "n"


def cumlelere_bol(t):
    """Talimatı fiillerinden bölerek [(metin, fiil)] döndürür; fiil: degis | kaldir | ekle | cikar."""
    out, bas = [], 0
    for m in re.finditer(r"(değiştiril|yeniden düzenlen|yürürlükten kaldırıl|kaldırıl|eklen|çıkarıl|ilga edil)\w*", t):
        if re.match(r"\s*(?:mış|miş|muş|müş)?(?:tır|tir|tur|tür)?\s*[.,]|\s+(?:ve|ile)\s+", t[m.end():]) or m.end() >= len(t) - 2 or True:
            parca = t[bas:m.end()]
            # 'gelmek üzere ... eklenmiş' ve 'şeklinde' içeren parçalar tek fiile aittir
            f = m.group(1)
            fiil = "degis" if f.startswith(("değiş", "yeniden")) else "ekle" if f.startswith("eklen") else "cikar" if f.startswith("çıkar") else "kaldir"
            out.append([parca, fiil])
            bas = m.end()
    return out


def _sayilar(s):
    return [SIRA[x.lower()] for x in re.findall(r"(" + SIRA_RE + r")", s, re.I)] + [int(x) for x in re.findall(r"\((\d+)\)", s)]


def yollari_coz(metin, bag):
    """Bir cümledeki hedef yollar; bag: önceki bağlam {m,f,b}. Döner: (yollar, bağlam, ibare_kapsami, capa)"""
    yollar, cur, kapsam, capa = [], dict(bag), None, None
    for tk in _TOK.finditer(metin):
        g = tk.lastgroup
        if g == "bo":
            yollar.append({"bolum": SIRA[tk.group("bon").lower()]})
        elif g == "m":
            cur = {"m": madde_anahtari(tk.group("mt") or "", tk.group("mn"), tk.group("mh"))}
            et = _ek_tur(tk.group("ms"))
            if et == "n" or et == "y":
                for x in re.findall(r"\d+", tk.group("mliste") or ""):
                    yollar.append({"m": madde_anahtari(tk.group("mt") or "", x), "ek": et})
                yollar.append(dict(cur, ek=et))
            elif et == "c":
                capa = dict(cur)
        elif g == "am":
            cur = {"m": cur.get("m") or bag.get("m")}
            if _ek_tur(tk.group("am")[11:]) == "y":
                yollar.append(dict(cur, ek="y"))
        elif g == "af":
            cur = {"m": cur.get("m"), "f": cur.get("f") or bag.get("f")}
            if _ek_tur(tk.group("af")[10:]) == "y":
                yollar.append(dict(cur, ek="y"))
        elif g == "ab":
            cur = {"m": cur.get("m"), "f": cur.get("f"), "b": cur.get("b") or bag.get("b")}
        elif g == "f":
            nolar = _sayilar(tk.group("f"))
            if re.search(r"\bson\s+fıkra", tk.group("f"), re.I):
                nolar.append("son")
            et = _ek_tur(tk.group("fs"))
            base = {"m": cur.get("m")}
            if et in ("n", "y"):
                yollar += [dict(base, f=n, ek=et) for n in nolar]
                cur = dict(base, f=nolar[-1])
            elif et == "c":
                capa = dict(base, f=nolar[-1])
            else:
                cur = dict(base, f=nolar[-1])
        elif g == "b":
            har = re.findall(r"\(([a-zçğıöşü]{1,2})\)", tk.group("b"))
            et = _ek_tur(tk.group("bs"))
            base = {"m": cur.get("m"), "f": cur.get("f")}
            if et in ("n", "y"):
                yollar += [dict(base, b=x, ek=et) for x in har]
                cur = dict(base, b=har[-1])
            elif et == "c":
                capa = dict(base, b=har[-1])
            else:
                cur = dict(base, b=har[-1])
        elif g == "a":
            nolar = [int(x) for x in re.findall(r"\((\d+)\)", tk.group("a"))]
            et = _ek_tur(tk.group("as"))
            base = {"m": cur.get("m"), "f": cur.get("f"), "b": cur.get("b")}
            if et in ("n", "y"):
                yollar += [dict(base, a=n, ek=et) for n in nolar]
            elif et == "c":
                capa = dict(base, a=nolar[-1])
            else:
                cur = dict(base, a=nolar[-1])
        elif g == "c":
            cn = tk.group("cn").lower()
            for x in _sayilar(tk.group("cl") or ""):
                yollar.append({"m": cur.get("m"), "f": cur.get("f"), "b": cur.get("b"), "c": x, "ek": _ek_tur(tk.group("cs"))})
            yollar.append({"m": cur.get("m"), "f": cur.get("f"), "b": cur.get("b"), "c": "son" if cn == "son" else SIRA[cn], "ek": _ek_tur(tk.group("cs"))})
        elif g == "h":
            yollar.append({"m": cur.get("m"), "h": 1})
        elif g == "ib" and kapsam is None:
            kapsam = dict(cur)
    return yollar, cur, kapsam, capa


def birim_bul(belge, yol):
    """Yolun paragraf aralığı (bas, son, madde_bas) ya da None."""
    r = belge.madde(yol.get("m")) if yol.get("m") else None
    if not r:
        return None
    i, j = r
    if not any(yol.get(x) is not None for x in ("f", "b", "a")):
        return i, j, i
    bl = birimler(belge.p, i, j)
    aday = bl
    if yol.get("f") is not None:
        f = yol["f"]
        if f == "son":
            f = next((u[1] for u in reversed(bl) if u[0] == "f"), None)
        aday = [u for u in aday if u[4] == f]
        if yol.get("b") is None and yol.get("a") is None:
            aday = [u for u in aday if u[0] == "f"]
    if yol.get("b") is not None:
        aday = [u for u in aday if u[5] == yol["b"]]
        if yol.get("a") is None:
            aday = [u for u in aday if u[0] == "b"]
    if yol.get("a") is not None:
        aday = [u for u in aday if u[0] == "a" and u[1] == yol["a"]]
    if len(aday) != 1:
        return None
    return aday[0][2], aday[0][3], i


_ONEK = re.compile(r"^(\**\s*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+\s*(?:/\s*[A-Za-z])?\s*\.?\s*\**\s*[-–—]\s*\**\s*)")


def _degistir(belge, bas, son, mbas, yeni):
    par = belge.p
    onek = ""
    if bas == mbas and yeni and not MADDE_BAS.match(yeni[0].replace("**", "")):
        m = _ONEK.match(par[bas])
        onek = m.group(1) if m else ""
    if onek:
        yeni = [onek + yeni[0]] + yeni[1:]
    par[bas:son] = yeni


def _etiketi(p):
    d = ETIKET.sub("", p.replace("**", ""), count=1).strip()
    m = re.match(r"^(\(\d+\)|[a-zçğıöşü]{1,2}\)|\d+\))", d)
    return m.group(1) if m else ""


def yuk_gruplari(yuk):
    """Yükü atomik birimlere böler: her tırnak bloğu ve blok içindeki aynı düzeydeki her etiketli birim ayrı;
    alt düzey (bent, alt bent) üstüne bağlı kalır; maddeden önceki başlık satırı maddeye katılır."""
    bloklar = []
    for p in yuk:
        if p.lstrip("*# ").startswith("“") or not bloklar:
            bloklar.append([p])
        else:
            bloklar[-1].append(p)
    sev = {"(": 0, "a": 1, "1": 2}
    out = []
    for bl in bloklar:
        bl = yuk_birimleri(bl)
        if not bl:
            continue
        ust = None
        for n, p in enumerate(bl):
            d = p.replace("**", "")
            if MADDE_BAS.match(d):
                tip = "M"
            else:
                e = etiket(p)
                tip = {"f": "(", "b": "a", "a": "1"}[e[0]] if e else None
            if ust is None:
                ust = tip
                out.append([p])
            elif tip == ust and tip is not None and not (out[-1] and len(out[-1]) == 1 and _baslik_mi(out[-1][0]) and tip == "M"):
                out.append([p])
            else:
                out[-1].append(p)
            if ust is None and n == 0 and _baslik_mi(p):
                ust = None
    # baş satırı yalnız başlık olan birim sonraki madde birimiyle birleşsin
    birles = []
    for g in out:
        if birles and len(birles[-1]) == 1 and _baslik_mi(birles[-1][0]) and g and MADDE_BAS.match(g[0].replace("**", "")):
            birles[-1] += g
        else:
            birles.append(g)
    return birles


def uygula2(belge, talimat, yuk, kunye, bag):
    t = " ".join(talimat.split())
    m = re.search(r"yayımlanan\s+(.+?)(?:Yönetmeliğin|Yönetmeliğine|Yönetmeliğe|Tebliğin|Tebliğe|Tüzüğün|Tüzüğe|Yönergenin)\b", t)
    if m and getattr(belge, "baslik", None):
        k1 = {w[:6] for w in sade(belge.baslik).split() if len(w) > 3} - {"yoneti", "teblig", "hakkin"}
        k2 = {w[:6] for w in sade(m.group(1)).split() if len(w) > 3} - {"yoneti", "teblig", "hakkin"}
        belge.aktif = bool(k1) and len(k1 & k2) / len(k1) >= 0.6
    elif not re.match(r"Aynı\s", t) and re.search(r"Yönetmeliğin|Tebliğin", t) and not re.search(r"Bu Yönetmeli|Bu Tebli", t):
        pass
    if getattr(belge, "no", None):
        m2 = re.search(r"(\d{3,4})\s*sayılı", t)
        if m2 and not re.match(r"Aynı\s", t):
            belge.aktif = m2.group(1) == belge.no
    if getattr(belge, "aktif", True) is False:
        return None, [], bag
    if not re.search(r"maddes|madde\w*\s|fıkra|bend|bent|bölüm|ibare", t):
        return None, [], bag
    if re.search(r"yürürlüğe girer|hükümlerini .* yürütür", t) and not re.search(r"maddes|ibare", t):
        return None, [], bag
    genel = re.search(r"(Yönetmeli\w*|Tebliğ\w*|Yönerge\w*|Tüzü\w*)\s+(?:geçen|yer alan|bulunan)\s*“|metninde geçen", t)
    gruplar = yuk_gruplari(yuk)
    hepsi = sum(gruplar, [])
    cumleler = cumlelere_bol(t)
    if not cumleler:
        return False, [], bag
    etk, tamam, kalan = [], True, list(gruplar)
    for n, (parca, fiil) in enumerate(cumleler):
        yollar, bag, kapsam, capa = yollari_coz(parca, bag)
        ibare = re.findall(r"“([^”]*)”\s*(?:ibare|ifade|kelime|sözcük|rakam)(?:si|leri|ı|i|leri)\s*“([^”]*)”\s*şeklinde", parca)
        ek_ib = re.findall(r"“([^”]+)”\s*(?:ibare|ifade|kelime|sözcük|rakam)\w*\s*(önce|sonra)\s*gelmek üzere\s*“([^”]*)”\s*(?:ibare|ifade|kelime|sözcük|rakam)", parca)
        sil_ib = re.findall(r"“([^”]+)”\s*(?:ibare|ifade|kelime|sözcük|rakam)(?:si|leri|ı|i|leri)\s*(?:yürürlükten kaldırıl|madde metninden çıkarıl|metinden çıkarıl|çıkarıl)", parca)
        if fiil == "cikar" and not (ibare or ek_ib or sil_ib) and re.search(r"madde metinlerinden\s+çıkarıl", parca) and re.search(r"[“\"]", parca) and re.search(r"ibare|ifade|kelime|sözcük|rakam", parca):
            # İbare hedefi çözülemediyse madde veya fıkranın tamamını silme.
            tamam = False
            continue
        if ibare or ek_ib or sil_ib:
            if genel and not kapsam.get("m") if kapsam else genel:
                alan = (0, len(belge.p))
                hedef_m = "*"
            else:
                kp = kapsam or bag
                r = birim_bul(belge, {k: v for k, v in kp.items() if k in ("m", "f", "b", "a")})
                if not r:
                    tamam = False
                    continue
                alan = (r[0], r[1])
                hedef_m = kp.get("m")
            degisti = False
            tumu = re.search(r"ibareleri", parca)
            for x in range(*alan):
                y = belge.p[x]
                for es, ye in ibare:
                    y = y.replace(es, ye) if tumu or alan[1] - alan[0] > 50 else y.replace(es, ye, 1)
                for once, yon, ek in ek_ib:
                    if once in y:
                        y = y.replace(once, (ek + " " + once) if yon == "önce" else (once + ("" if ek[:1] in ",;.)" else " ") + ek), 1)
                for s in sil_ib:
                    if s in y:
                        y = re.sub(r"\s?" + re.escape(s), "", y, count=1)
                if y != belge.p[x]:
                    belge.p[x] = y
                    degisti = True
            if not degisti:
                tamam = False
            etk.append(hedef_m)
            continue
        if not yollar:
            if fiil == "ekle" and kalan and re.search(r"aşağıdaki\s+(?:geçici\s+|ek\s+)?madde", parca):
                yeni = sum(kalan, [])
                kalan = []
                keys = [madde_anahtari(m.group(1), m.group(2), m.group(3)) for m in (MADDE_BAS.match(p.replace("**", "")) for p in yeni) if m]
                if not keys:
                    tamam = False
                    continue
                if capa and capa.get("m") and belge.madde(capa["m"]):
                    yer = belge.madde(capa["m"])[1]
                    while yer < len(belge.p) and _baslik_mi(belge.p[yer]) and not MADDE_BAS.match(belge.p[yer].replace("**", "")):
                        yer += 1
                else:
                    yer = _ek_yeri(belge, keys[0])
                belge.p[yer:yer] = _not_ekle(yeni, f"(Ek:RG-{kunye})")
                etk += keys
                continue
            tamam = False
            continue
        for y in yollar:
            if y.get("bolum"):
                bas_ = [x for x, p in enumerate(belge.p) if re.match(r"^\W*" + [k for k, v in SIRA.items() if v == y["bolum"]][0].upper().replace("İ", "İ") + r"\s+BÖLÜM", p.replace("**", ""), re.I)]
                yb = re.search(r"başlığı\s*“([^”]+)”", parca)
                if bas_ and yb and bas_[0] + 1 < len(belge.p):
                    belge.p[bas_[0] + 1] = yb.group(1)
                else:
                    tamam = False
                continue
            if y.get("h"):
                yb = re.search(r"başlığı\s*“([^”]+)”", parca)
                r = belge.madde(y["m"])
                if r and yb and r[0] > 0 and _baslik_mi(belge.p[r[0] - 1]):
                    belge.p[r[0] - 1] = yb.group(1)
                    etk.append(y["m"])
                elif r and fiil == "degis" and re.search(r"başlığı ile birlikte", t):
                    pass
                else:
                    tamam = False
                continue
        yol_ = [y for y in yollar if not y.get("bolum") and not y.get("h")]
        if not yol_ and fiil == "ekle" and re.search(r"sonuna|başına", parca) and bag.get("m"):
            yol_ = [dict(bag, ek="y")]
            if re.search(r"cümle", parca):
                yol_[0]["cumle_ekle"] = 1
        if not yol_:
            continue
        if fiil == "degis" and re.search(r"aşağıdaki şekilde|şu şekilde", parca):
            if "c" in yol_[0] and len(yol_) > 1 and all("c" in y for y in yol_):
                r = birim_bul(belge, {k: v for k, v in yol_[0].items() if k in ("m", "f", "b", "a")} | ({} if yol_[0].get("f") else {"f": 1}))
                if not r or not kalan:
                    tamam = False
                    continue
                g = kalan.pop(0)
                x = r[0]
                cs = re.split(r"(?<=[.])\s+(?=[A-ZÇĞİÖŞÜ(“])", belge.p[x])
                nolar = sorted(y["c"] if y["c"] != "son" else len(cs) for y in yol_)
                if nolar[0] >= 1 and nolar[-1] <= len(cs):
                    cs[nolar[0] - 1:nolar[-1]] = [" ".join(g)]
                    belge.p[x] = " ".join(cs)
                    etk.append(yol_[0]["m"])
                else:
                    tamam = False
                continue
            if "c" in yol_[0]:
                r = birim_bul(belge, {k: v for k, v in yol_[0].items() if k in ("m", "f", "b", "a")} | ({} if yol_[0].get("f") else {"f": 1}))
                if not r or not kalan:
                    tamam = False
                    continue
                g = kalan.pop(0)
                x = r[0]
                cs = re.split(r"(?<=[.])\s+(?=[A-ZÇĞİÖŞÜ(“])", belge.p[x])
                c = len(cs) if yol_[0]["c"] == "son" else yol_[0]["c"]
                if 1 <= c <= len(cs):
                    cs[c - 1] = " ".join(g)
                    belge.p[x] = " ".join(cs)
                    etk.append(yol_[0]["m"])
                else:
                    tamam = False
                continue
            # yük grubu sayısı yol sayısından azsa grubu üst etiketlere böl
            if len(kalan) < len(yol_) and kalan:
                bol = []
                for p in kalan[0]:
                    if not bol or (_etiketi(p) and _etiketi(p)[0] == _etiketi(kalan[0][0])[:1] and _etiketi(kalan[0][0])):
                        bol.append([p])
                    else:
                        bol[-1].append(p)
                kalan = bol + kalan[1:]
            for y in yol_:
                if not kalan:
                    tamam = False
                    break
                g = kalan.pop(0)
                if y.get("m") and not any(y.get(x) is not None for x in ("f", "b", "a")):
                    r = belge.madde(y["m"])
                    if not r:
                        tamam = False
                        continue
                    if re.search(r"başlığı ile birlikte", parca) and g and not MADDE_BAS.match(g[0].replace("**", "")):
                        if r[0] > 0 and _baslik_mi(belge.p[r[0] - 1]):
                            belge.p[r[0] - 1] = g[0]
                        g = g[1:]
                    belge.p[r[0]:r[1]] = _not_ekle(g, f"(Değişik:RG-{kunye})")
                else:
                    r = birim_bul(belge, y)
                    if not r:
                        tamam = False
                        continue
                    _degistir(belge, r[0], r[1], r[2], _not_ekle(g, f"(Değişik:RG-{kunye})"))
                etk.append(y["m"])
            continue
        if fiil in ("kaldir", "cikar"):
            for y in sorted(yol_, key=lambda y: -(birim_bul(belge, y) or (0,))[0]):
                if "c" in y:
                    r = birim_bul(belge, {k: v for k, v in y.items() if k in ("m", "f", "b", "a")} | ({} if y.get("f") else {"f": 1}))
                    if not r:
                        tamam = False
                        continue
                    x = r[0]
                    cs = re.split(r"(?<=[.])\s+(?=[A-ZÇĞİÖŞÜ(“])", belge.p[x])
                    c = len(cs) if y["c"] == "son" else y["c"]
                    if 1 <= c <= len(cs):
                        del cs[c - 1]
                        belge.p[x] = " ".join(cs)
                        etk.append(y["m"])
                    continue
                r = birim_bul(belge, y)
                if not r:
                    tamam = False
                    continue
                if not any(y.get(x) is not None for x in ("f", "b", "a")):
                    m = _ONEK.match(belge.p[r[0]])
                    belge.p[r[0]:r[1]] = [(m.group(1) if m else "") + f"(Mülga:RG-{kunye})"]
                else:
                    lab = _etiketi(belge.p[r[0]])
                    _degistir(belge, r[0], r[1], r[2], [f"{lab} (Mülga:RG-{kunye})".strip()])
                etk.append(y["m"])
            continue
        if fiil == "ekle":
            if not kalan:
                tamam = False
                continue
            cok = re.search(r"aşağıdaki\s+\w*\s*(fıkralar|bentler|cümleler|maddeler)", parca) or n == len(cumleler) - 1
            yeni = sum(kalan, []) if cok else kalan[0]
            kalan = [] if cok else kalan[1:]
            y = yol_[-1]
            if re.search(r"cümle", parca) and (y.get("ek") == "y" or y.get("cumle_ekle")):
                r = birim_bul(belge, {k: v for k, v in y.items() if k in ("m", "f", "b", "a")})
                if not r:
                    tamam = False
                    continue
                x = r[0]
                while x + 1 < r[1] and not etiket(belge.p[x + 1]) and False:
                    x += 1
                belge.p[x] = belge.p[x].rstrip() + " " + " ".join(yeni)
                etk.append(y["m"])
                continue
            hedef = capa if capa else y
            r = birim_bul(belge, {k: v for k, v in hedef.items() if k in ("m", "f", "b", "a")})
            if not r:
                tamam = False
                continue
            if capa:
                yer = r[1]
            else:
                yer = r[1]
            belge.p[yer:yer] = _not_ekle(yeni, f"(Ek:RG-{kunye})")
            etk.append(hedef.get("m"))
            continue
        tamam = False
    return tamam, [e for e in etk if e], bag



# ---------------------------------------------------------------- karşılaştırma
def norm(s):
    # Aynı dipnot numarası bazen köşeli atıfla birlikte üç noktanın
    # ardından düz metin olarak da aktarılır; hukuk metnindeki sayıları koru.
    for n in set(re.findall(r"\[(\d+)\]", s)):
        s = re.sub(r"(\(\s*(?:…|\.{3})\s*\))\s*" + re.escape(n) + r"\s*(?=[,.;:])", r"\1", s)
    s = NOT.sub(" ", s)
    s = re.sub(r"\[\d+\]|\*\*|#+|[“”\"'’‘]|<[^>]+>", " ", s)
    return sade(s)


_ARTIK = re.compile(r"^\W*[A-ZÇĞİÖŞÜ]+\s+(BÖLÜM|KISIM)|^<small>|^_{3,}|^-{3,}|^\[\d+\]|^\(\d+\)\s*(Bu değişiklik|Bu madde)|tıklayınız|^Yönetmeli\w* ekleri|^Ek-?\s*\d+\s*[-–:]?\s*\[|^\|", re.I)


def madde_metinleri(belge):
    out = {}
    for k, i, j in belge.maddeler():
        ps = []
        for p in belge.p[i:j]:
            if _ARTIK.search(p.strip()):
                if ps:
                    break  # dipnot/ek bağlantısı: maddenin sonu
                continue
            ps.append(p)
        out[k] = norm(" ".join(ps))
    return out


def rg_md(url, baslik=None):
    if url.split("#")[0].lower().endswith(".pdf"):
        return pdf_md(url)
    ham = coz(getir(url.split("#")[0]))
    # Cumhurbaşkanı Kararı sayfası: yönetmelik metni ekli PDF'tedir
    if not re.search(r"(?:MADDE|Madde)\s*\d+", html.unescape(re.sub(r"<[^>]+>", " ", ham))):
        ek = re.findall(r'href="([^"]+-\d+\.pdf)"', ham)
        if ek:
            import urllib.parse
            return pdf_md(urllib.parse.urljoin(url, ek[0]))
    # içindekiler (fihrist/mükerrer) sayfası geldiyse içinden doğru bağlantıyı bul
    if baslik and len(re.findall(r'href="[^"]*\d{8}[^"]*\.htm', ham)) >= 3 and not re.search(r"MADDE\s*1\s*[-–]", ham):
        from surum_indir import esles
        import urllib.parse
        baglar = []
        for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', ham):
            mt = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
            if len(mt) > 8:
                baglar.append((urllib.parse.urljoin(url, m.group(1)), mt))
        e = esles(baglar, baslik, False) or esles(baglar, baslik, True)
        if e:
            ham = coz(getir(e[0]))
    # tek sayfalık eski gazete: yalnız ilgili çapa bölümü
    if "#" in url:
        capa = url.split("#")[1]
        m = re.search(r'(?i)<a\s+name="?' + re.escape(capa) + r'"?', ham)
        if m:
            n = re.search(r'(?i)<a\s+name="?\d+"?', ham[m.end():])
            ham = ham[m.start(): m.end() + (n.start() if n else len(ham))]
    md = html_md(ham)
    # RG sayfa başlığını ve künye satırlarını at: ilk ### başlıktan önceki kısım
    return md


def pdf_md(url):
    """RG PDF'i (metin katmanlı ya da taranmış) → paragraflı metin. Sayfa metinleri
    kaynak-isleme/indirilen/rg-surum-pdf/<ad>/ altında önbelleğe alınır (pdf_sayfa_metin.py; pdfplumber,
    pypdfium2 ve Tesseract gerekir: PYTHONPATH ile)."""
    import os, subprocess
    getir(url)
    from surum_indir import ON
    ad = re.sub(r"[^A-Za-z0-9.-]+", "_", url.split("://", 1)[-1])[-150:]
    klasor = ON.parent / "rg-surum-pdf" / ad
    if not any(klasor.glob("p*.txt")):
        subprocess.run([sys.executable, str(KOK / "araclar" / "pdf_sayfa_metin.py"), str(ON / ad), str(klasor)],
                       env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "/private/tmp/pylib")}, capture_output=True)
    from ocr_ilk_metin import paragraflar as ocr_par
    md = "\n\n".join(ocr_par([f.read_text(encoding="utf-8") for f in sorted(klasor.glob("p*.txt"))]))
    # okumada talimat ile tırnaklı metin aynı paragrafa düşmüşse ayır
    return re.sub(r"((?:eklenmiş|değiştirilmiş|düzenlenmiş|kaldırılmış)(?:tir|tır)\.)\s+(“)", r"\1\n\n\2", md)


def govde_al(dosya):
    s = Path(dosya).read_text(encoding="utf-8")
    s = s[s.index("\n---\n", 4) + 5:]
    # sondaki değişiklik listesini at (kanunlarda baştaki künyede de "Yayımlandığı Resmî Gazete" geçer)
    m = re.search(r"\n#+\s*\d+\s*SAYILI\s*(?:KANUN|KHK)\w*\s*EK VE DEĞİŞİKLİK", s)
    i = m.start() if m else -1
    if i < 0:
        # yalnız ilk maddeden sonraki "Yayımlandığı Resmî Gazete" (baştaki künye satırları sayılmaz)
        ilk_md = re.search(r"(?:MADDE|Madde)\s*1\s*\.?\s*\**\s*[-–—]", s)
        bas = max(ilk_md.start() if ilk_md else 0,
                  1500 if re.search(r"Kanun Numarası|KHK Numarası|Kararname Numarası", s[:1500]) else 0)
        i = s.find("Yayımlandığı Resmî Gazete", bas)
    if i > 0:
        s = s[:s.rfind("\n", 0, i)]
    return s


def ilk_metni_kirp(md, baslik, no=None):
    """RG sayfasından yönetmeliğin kendisi: başlığa en çok benzeyen ve ardından ilk madde olarak MADDE 1 gelen
    başlık satırı grubundan sonuna."""
    par = paragraflar(md)
    hedef = sade(re.sub(r"\(.*?\)", " ", baslik))
    iyi = (0, None)
    for n, p in enumerate(par):
        if not p.startswith("#") or (n and par[n - 1].startswith("#")):
            continue
        grup, x = [], n
        while x < len(par) and par[x].startswith("#") and len(grup) < 5:
            grup.append(par[x])
            x += 1
        bas = sade(" ".join(grup).replace("#", ""))
        ilk_m = next((q for q in par[x:x + 15] if re.search(r"^\W*(MADDE|Madde)\s*\d+", q.replace("**", ""))), "")
        if not re.search(r"^\W*(MADDE|Madde)\s*1\s*[-–—.:]", ilk_m.replace("**", "")):
            continue
        oran = difflib.SequenceMatcher(None, bas, hedef).ratio()
        if hedef and hedef in bas:
            oran = max(oran, 0.95)
        if oran >= iyi[0]:
            iyi = (oran, n)
    return "\n\n".join(par[iyi[1]:]) if iyi[1] is not None and iyi[0] >= 0.6 else md


def ilk_madde_basliklarini_ayir(md):
    """Bazı eski RG metinlerinde madde başlığı ve MADDE aynı paragraftadır."""
    out = []
    for p in paragraflar(md):
        m = re.match(r"^([^\n]{1,120}?)\s+((?:(?:GEÇİCİ|Geçici|EK|Ek)\s+)?(?:MADDE|Madde)\s*\d+\s*(?:/\s*[A-Za-z])?\s*\.?\s*[-–—])", p)
        if m and not re.search(r"(?:^|\s)(?:GEÇİCİ|Geçici|EK|Ek)$", m.group(1).strip('* "“')) and not re.search(r"[.;:!?]", m.group(1)):
            out.extend([m.group(1), p[m.start(2):]])
        else:
            out.append(p)
    return "\n\n".join(out)


def isle(kimlik, kayit, dosya):
    sonuc = {"baslik": kayit["baslik"], "surumler": [], "uyari": []}
    if not kayit["ilk"].get("url"):
        sonuc["uyari"].append("İlk yayım metni Resmî Gazete'de bulunamadı.")
        return sonuc
    if kayit["ilk"].get("md"):  # RG'de yalnız taranmış PDF: görüntüden okunmuş ilk metin
        ilk = ilk_metni_kirp((KOK / kayit["ilk"]["md"]).read_text(encoding="utf-8"), kayit["baslik"])
    else:
        ilk = ilk_metni_kirp(rg_md(kayit["ilk"]["url"], kayit["baslik"]), kayit["baslik"])
    belge = Belge(ilk_madde_basliklarini_ayir(ilk))
    belge.baslik = kayit["baslik"]
    belge.no = kayit.get("no")
    sonuc["surumler"].append({"t": kayit["ilk"]["t"], "sayi": kayit["ilk"]["sayi"], "url": kayit["ilk"]["url"], "tur": "ilk",
                              "md": "\n\n".join(belge.p), "degisen": [], "basarisiz": []})
    for d in sorted(kayit["deg"], key=lambda x: x["t"]):
        g, a, y = d["t"][8:], d["t"][5:7], d["t"][:4]
        kunye = f"{int(g)}/{int(a)}/{y}-{d['sayi']}"
        kay = {"t": d["t"], "sayi": d["sayi"], "url": d.get("url"), "ad": d.get("ad"), "degisen": [], "basarisiz": []}
        if not d.get("url"):
            kay["basarisiz"].append("Değişiklik metni Resmî Gazete'de bulunamadı")
        else:
            onceki = {}
            belge.aktif = True
            for talimat, yuk, mno in degisiklik_maddeleri(rg_md(d["url"], kayit["baslik"])):
                if d.get("maddeler") and mno not in d["maddeler"]:
                    continue
                try:
                    ok, etk, onceki = uygula2(belge, talimat, yuk, kunye, onceki)
                except Exception as h:  # noqa: BLE001
                    ok, etk = False, []
                if ok is None:
                    continue
                if ok:
                    kay["degisen"] += [x for x in etk if x not in kay["degisen"]]
                else:
                    kay["basarisiz"].append(talimat[:300])
        kay["md"] = "\n\n".join(belge.p)
        sonuc["surumler"].append(kay)
    # doğrulama: son sürüm ile güncel metin
    guncel = madde_metinleri(Belge(govde_al(dosya)))
    son = madde_metinleri(belge)
    dog = {}
    for k, v in guncel.items():
        w = son.get(k)
        dog[k] = bool(w) and (w == v or difflib.SequenceMatcher(None, w, v, autojunk=False).ratio() >= 0.97)
    sonuc["dogrulama"] = dog
    sonuc["fazla"] = [k for k in son if k not in guncel]
    return sonuc


def main():
    indeks = json.loads((KOK / "kaynak-isleme" / "surum" / "indeks.json").read_text())
    secim = sys.argv[1:] or list(indeks)
    dosyalar = {p.stem: p for p in (KOK / "icerik").glob("*/*.md")}
    toplam = [0, 0]
    for kimlik in secim:
        if kimlik not in indeks or kimlik not in dosyalar:
            continue
        s = isle(kimlik, indeks[kimlik], dosyalar[kimlik])
        (KOK / "kaynak-isleme" / "surum" / f"{kimlik}.json").write_text(json.dumps(s, ensure_ascii=False, indent=0), encoding="utf-8")
        d = s.get("dogrulama", {})
        toplam[0] += sum(d.values())
        toplam[1] += len(d)
        bs = sum(len(x["basarisiz"]) for x in s["surumler"])
        print(f"{sum(d.values())}/{len(d)} madde doğru, {bs} uygulanamayan talimat  {kimlik[:60]}", flush=True)
    print("TOPLAM", toplam)


if __name__ == "__main__":
    main()

