#!/usr/bin/env python3
"""Değişikliğe uğramış RG mevzuatının ilk yayım metnini ve değişiklik metinlerini Resmî Gazete'den indirir.
Girdi: icerik/ içindeki mevzuat.gov.tr metinlerinin sonundaki RG tablosu. Çıktı: kaynak-isleme/surum/indeks.json
ve kaynak-isleme/indirilen/rg-surum/ (HTML önbelleği).
Kullanım: python araclar/surum_indir.py [--tur yonetmelik,teblig,tuzuk]"""
import html, json, re, subprocess, sys, time, unicodedata
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
ON = KOK / "kaynak-isleme" / "indirilen" / "rg-surum"
INDEKS = KOK / "kaynak-isleme" / "surum" / "indeks.json"
T = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def sade(s):
    s = unicodedata.normalize("NFKD", (s or "").replace("İ", "i").replace("I", "ı").lower())
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("ı", "i")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def getir(url):
    ON.mkdir(parents=True, exist_ok=True)
    yol = ON / re.sub(r"[^A-Za-z0-9.-]+", "_", url.split("://", 1)[-1])[-150:]
    if yol.exists() and yol.stat().st_size > 200:
        return yol.read_bytes()
    for _ in range(3):
        r = subprocess.run(["curl", "-sL", "--max-time", "60", "-A", "Mozilla/5.0", url], capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 200:
            yol.write_bytes(r.stdout)
            time.sleep(0.4)
            return r.stdout
        time.sleep(2)
    return b""


def coz(ham):
    for kod in ("utf-8", "windows-1254", "iso-8859-9"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            pass
    return ham.decode("utf-8", "replace")


def fihrist(t):
    y, a, g = t.split("-")
    url = f"https://www.resmigazete.gov.tr/eskiler/{y}/{a}/{y}{a}{g}.htm"
    s = coz(getir(url))
    out = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', s):
        metin = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split()).strip("–- \xa0")
        if len(metin) > 8:
            import urllib.parse
            out.append((urllib.parse.urljoin(url, m.group(1)), metin))
    return out


def tablo(s):
    i = s.find("Yayımlandığı Resmî Gazete")
    if i < 0:
        return None, []
    ilk, deg, bolum = None, [], 0
    for l in s[i:].split("\n"):
        if not l.startswith("|"):
            continue
        if re.search(r"Değişiklik Yapan|Değiştiren", l):
            bolum = 1
            continue
        c = [x.strip() for x in l.strip("|").split("|")]
        d = [x for x in c if T.fullmatch(x)]
        n = [x for x in c if re.match(r"^\d{4,5}\b", x) and not T.fullmatch(x)]
        if d:
            g, a, y = T.fullmatch(d[0]).groups()
            t = f"{y}-{int(a):02d}-{int(g):02d}"
            if bolum == 0 and not ilk:
                ilk = [t, n[0] if n else ""]
            elif bolum:
                deg.append([t, n[0] if n else ""])
    return ilk, deg


def anahtar(baslik):
    s = sade(re.sub(r"\(.*?\)", " ", baslik))
    return [w for w in s.split() if len(w) > 3 and w not in ("yonetmelik", "yonetmeligi", "hakkinda", "dair", "iliskin", "tebligi", "teblig")]


def esles(baglar, baslik, degisiklik):
    """Fihristteki bağlantılardan başlığa en uygun olanı. Önce başlığın sade hâlinin bağlantıda geçmesine bakılır;
    yoksa anahtar sözcüklerin hepsinin (kısa olanlar dahil) geçmesi aranır."""
    cekirdek = sade(re.sub(r"\(.*?\)", " ", baslik))
    cekirdek = re.sub(r"\b(yonetmeligi|yonetmelik|tebligi|teblig|tuzugu|tuzuk)$", "", cekirdek).strip()
    sozc = [w for w in cekirdek.split() if w not in ("ve", "ile", "hakkinda", "dair", "iliskin")]
    iyi = (0, None)
    for u, m in baglar:
        sm = sade(m)
        if degisiklik != bool(re.search(r"degisiklik yapil|degistirilmesine|degisiklik yapan", sm)):
            continue
        if not degisiklik and re.search(r"yururlukten kaldirilmasina|yururluge konulmasina", sm):
            continue
        if cekirdek and cekirdek in sm:
            p = 2.0 - (len(sm) - len(cekirdek)) / 500
        else:
            p = sum(1 for w in sozc if re.search(r"\b" + re.escape(w[:max(3, len(w) - 3)]), sm)) / max(1, len(sozc))
        if p > iyi[0]:
            iyi = (p, (u, m))
    return iyi[1] if iyi[0] >= (0.9 if len(sozc) <= 4 else 0.8) else None


def ek_ara(t, sayi, baslik):
    """Mükerrer sayılar ve 'Bazı Yönetmeliklerde Değişiklik' türü toplu metinler."""
    y, a, g = t.split("-")
    baglar = list(fihrist(t))
    m = re.search(r"(\d)\s*\.?\s*mükerrer", sayi or "", re.I)
    for n in ([int(m.group(1))] if m else []) + [1, 2, 3, 4, 5]:
        try:
            baglar += fihrist_url(f"https://www.resmigazete.gov.tr/eskiler/{y}/{a}/{y}{a}{g}M{n}.htm")
        except Exception:
            pass
    e = esles(baglar, baslik, True)
    if e:
        return e
    cek = sade(re.sub(r"\(.*?\)", " ", baslik))
    cek = re.sub(r"\b(yonetmeligi|yonetmelik|tebligi|teblig)$", "", cek).strip()
    for u, mt in baglar:
        sm = sade(mt)
        if ("bazi" in sm or "degisiklik" in sm) and u.endswith(".htm"):
            icerik = sade(re.sub(r"<[^>]+>", " ", coz(getir(u))))
            if cek and cek in icerik:
                return (u, mt)
    return None


def fihrist_url(url):
    s = coz(getir(url))
    out = []
    import urllib.parse
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', s):
        metin = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split()).strip("–- \xa0")
        if len(metin) > 8:
            out.append((urllib.parse.urljoin(url, m.group(1)), metin))
    return out


def notlardan(s):
    """Değişiklik tablosu olmayan metinler (kitap, saglik.gov.tr): künyedeki RG tarihi/sayısı ilk metin,
    metindeki "(Değişik:RG-g/a/yyyy-sayı)" notları değişiklikler."""
    fm = s[:2500]
    rt = re.search(r'^rg_tarih: "(\d{4}-\d{2}-\d{2})"', fm, re.M)
    if not rt:
        return None, []
    rs = re.search(r'^rg_sayi: "(\d+)', fm, re.M)
    deg = set()
    for g, a, y, n in re.findall(r"\((?:Değişik|Ek|Mülga|Yeniden düzenleme)[^():]{0,40}:\s*RG\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d+)", s):
        t = f"{y}-{int(a):02d}-{int(g):02d}"
        if t > rt.group(1):
            deg.add((t, n))
    return (rt.group(1), rs.group(1) if rs else ""), sorted(deg)


def main():
    turler = ("yonetmelik", "teblig", "tuzuk")
    if "--tur" in sys.argv:
        turler = tuple(sys.argv[sys.argv.index("--tur") + 1].split(","))
    indeks = json.loads(INDEKS.read_text()) if INDEKS.exists() else {}
    dosyalar = [f for t in turler for f in sorted((KOK / "icerik" / t).glob("*.md"))]
    atla = set(sys.argv[sys.argv.index("--atla") + 1].split(",")) if "--atla" in sys.argv else set()
    for f in dosyalar:
        s = f.read_text(encoding="utf-8")
        if f.stem in atla:
            continue
        ilk, deg = tablo(s) if "mevzuat.gov.tr" in s[:2000] else (None, [])
        if not deg or not ilk:
            ilk, deg = notlardan(s)
        if not deg or not ilk:
            continue
        kimlik = re.search(r'^id: "([^"]+)"', s, re.M).group(1)
        baslik = re.search(r'^baslik: "([^"]+)"', s, re.M).group(1)
        k = indeks.get(kimlik) or {"baslik": baslik, "tur": f.parent.name, "ilk": {"t": ilk[0], "sayi": ilk[1]}, "deg": []}
        if not k["ilk"].get("url"):
            try:
                e = esles(fihrist(ilk[0]), baslik, False)
            except Exception as h:
                e = None
            if e:
                k["ilk"].update(url=e[0], ad=e[1])
        k["deg"] = [d for d in k["deg"] if d.get("url")]
        var = {(d["t"], d["sayi"]) for d in k["deg"]}
        for t, n in deg:
            if (t, n) in var:
                continue
            kay = {"t": t, "sayi": n}
            try:
                e = esles(fihrist(t), baslik, True) or ek_ara(t, n, baslik)
            except Exception:
                e = None
            if e:
                kay.update(url=e[0], ad=e[1])
            k["deg"].append(kay)
        for d in [k["ilk"]] + k["deg"]:
            if d.get("url"):
                getir(d["url"])
        indeks[kimlik] = k
        INDEKS.parent.mkdir(parents=True, exist_ok=True)
        INDEKS.write_text(json.dumps(indeks, ensure_ascii=False, indent=1), encoding="utf-8")
        tamam = sum(1 for d in [k["ilk"]] + k["deg"] if d.get("url"))
        print(f"{tamam}/{1 + len(k['deg'])}  {baslik[:70]}", flush=True)


if __name__ == "__main__":
    main()

