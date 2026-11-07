"""Taranmış sayfa görüntüsünden kelime bazında koyu/italik tahmini (macOS Vision kelime kutuları + çizgi kalınlığı/eğim)."""
import re, statistics, subprocess, numpy as np

OCRKUTU = "/tmp/ocrkutu"


def kelimeler(png):
    out = subprocess.run([OCRKUTU, png], capture_output=True, text=True).stdout
    W = H = 0; K = []
    for l in out.splitlines():
        p = l.split("\t")
        if p[0] == "SAYFA": W, H = int(p[2]), int(p[3])
        elif p[0] == "K" and len(p) >= 7:
            K.append((int(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5]), p[6]))
    return W, H, K


def _keskinlik(b, s):
    h, w = b.shape
    ys, xs = np.nonzero(b)
    if len(xs) == 0: return 0.0
    xp = np.round(xs + s * (ys - h / 2)).astype(int)
    xp -= xp.min()
    c = np.bincount(xp)
    return float((c.astype(float) ** 2).sum()) / max(1, len(xs)) ** 2 * len(c)


def _asin(b):
    e = b.copy()
    e[1:, :] &= b[:-1, :]; e[:-1, :] &= b[1:, :]; e[:, 1:] &= b[:, :-1]; e[:, :-1] &= b[:, 1:]
    e[0, :] = False; e[-1, :] = False; e[:, 0] = False; e[:, -1] = False
    return e


def stil(img_gri, W, H, K):
    a = np.asarray(img_gri)
    esik = a.mean() * 0.62
    ink = a < esik
    olc = []
    for li, x, y, w, h, t in K:
        x0, x1 = int(x * W), int((x + w) * W); y1, y0 = int((1 - y) * H), int((1 - y - h) * H)
        b = ink[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
        harf = len(re.sub(r"\W", "", t))
        if b.size == 0 or harf < 2:
            olc.append(None); continue
        if b.sum() < 20:
            olc.append(None); continue
        kalan = _asin(b).sum() / b.sum()
        k0 = _keskinlik(b, 0.0); kp = _keskinlik(b, 0.21); km = _keskinlik(b, -0.21)
        olc.append((kalan, b.mean(), max(kp, km) / max(k0, 1e-9), harf))
    gec = [o for o in olc if o]
    if len(gec) < 15:
        return [(t, False, False) for *_, t in K]
    m_sw = statistics.median(o[0] for o in gec); m_d = statistics.median(o[1] for o in gec)
    sonuc = []
    for (li, x, y, w, h, t), o in zip(K, olc):
        if not o: sonuc.append([t, False, False, li]); continue
        koyu = bool(o[0] >= m_sw * 1.4)
        italik = bool(o[3] >= 4 and o[2] >= 1.18)
        sonuc.append([t, koyu, italik, li])
    # koyu kelime ancak aynı satırda koyu komşusu varsa ya da satır en çok 2 kelimeyse kabul edilir
    satir_say = {}
    for r in sonuc: satir_say[r[3]] = satir_say.get(r[3], 0) + 1
    tut = []
    for j, r in enumerate(sonuc):
        komsu = any(0 <= q < len(sonuc) and sonuc[q][1] and sonuc[q][3] == r[3] for q in (j - 1, j + 1))
        tut.append(r[1] and (komsu or satir_say[r[3]] <= 2))
    for r, t in zip(sonuc, tut): r[1] = t
    return [(t, k, i) for t, k, i, _ in sonuc]


def parcalar(img_gri, png):
    W, H, K = kelimeler(png)
    S = stil(img_gri, W, H, K)
    out = []; onc = None
    for (li, *_), (t, k, i) in zip(K, S):
        if onc is not None and li != onc: out.append(("\x00", False, False))
        out.append((t + " ", k, i)); onc = li
    out.append(("\x00", False, False))
    return out

