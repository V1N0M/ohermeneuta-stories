import math, json, os, datetime
from PIL import Image, ImageDraw, ImageFont, ImageChops
from words import WORDS, SENT, R
import numpy as np
W, H = 1080, 1920
TM = json.load(open("tempos.json")); END0 = TM["END0"]; TOTAL = TM["TOTAL"]; CLICK = TM["CLICK"]
C = dict(navy=(16, 38, 63), base=(30, 58, 95), gold=(201, 162, 75), gold2=(217, 184, 101), goldV=(242, 201, 76), ivory=(248, 246, 242), out=(10, 22, 38), b4=(92, 130, 181))
PKG = os.path.dirname(os.path.abspath(__file__))
FD = PKG + "/assets/SourceSans3-VariableFont_wght.ttf"
_fc = {}
def font(sz, w=700):
    k = (sz, w)
    if k not in _fc:
        f = ImageFont.truetype(FD, sz)
        try: f.set_variation_by_axes([w])
        except Exception: pass
        _fc[k] = f
    return _fc[k]
GEO = None
for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",):
    GEO = p
def geo(sz, italic=False, bold=False):
    p = PKG + "/assets/DejaVuSerif" + ("-BoldItalic" if italic and bold else "-Italic" if italic else "-Bold" if bold else "") + ".ttf"
    return ImageFont.truetype(p, sz)
def k(t, a, b): return max(0.0, min(1.0, (t - a) / (b - a)))
def eout(x): return 1 - (1 - x) ** 3
def eio(x): return x * x * (3 - 2 * x)
def pop(t, t0, d=.45):
    x = k(t, t0, t0 + d)
    if x <= 0: return 0.0
    return 1 + 1.7 * (x - 1) ** 3 + .7 * (x - 1) ** 2 if x < 1 else 1.0
def tlen(d, s, f, ls=0): return d.textlength(s, font=f) + ls * len(s)
def stext(d, x, y, s, f, fill, ls=0, anchor="ls"):
    if ls == 0: d.text((x, y), s, font=f, fill=fill, anchor=anchor); return
    for ch in s: d.text((x, y), ch, font=f, fill=fill, anchor=anchor); x += d.textlength(ch, font=f) + ls
def A(c, a): return tuple(c) + (int(255 * max(0, min(1, a))),)

_assets = {}
def asset(n):
    if n not in _assets: _assets[n] = Image.open(PKG + "/assets/" + n).convert("RGBA")
    return _assets[n]

CAPS = [(lab, max(.15, SENT[i][0] - .4) if i > 0 else .15) for lab, i in R.get("capitulos", [])]
SEL = R.get("selo", "")
LABELS = [tuple(x) for x in R.get("chips", [])]          # (t0, t1, linha 0|1, texto) — opcional
ROTULO = R.get("rotulo_fixo", "ENCENAÇÃO ILUSTRATIVA")   # "" esconde
LANC = R.get("lancamento", "17-11-2026")
_d, _m, _y = [int(x) for x in LANC.split("-")]
DIA = str(_d); MES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"][_m - 1]
JA = datetime.date.today() >= datetime.date(_y, _m, _d)

def chunks():
    ch = []; cur = []; ln = 0
    for w in WORDS:
        txt = w[0]
        if cur and (w[3] != cur[-1][3] or ln + len(txt) + 1 > 40 or len(cur) >= 7 or cur[-1][0][-1] in ".?;:"):
            ch.append(cur); cur = []; ln = 0
        cur.append(w); ln += len(txt) + 1
    if cur: ch.append(cur)
    return ch
CH = chunks()

def draw_labels(ov, t):
    d = ImageDraw.Draw(ov)
    for (a, b, row, txt) in LABELS:
        if a <= t < b:
            al = min(1, (t - a) / .25, (b - t) / .25); f = font(34, 800); w = tlen(d, txt, f, 1.7) + 48; x = 90; y = 440 + row * 82 + int((1 - eout(min(1, (t - a) / .3))) * 14)
            d.rectangle([x, y, x + w, y + 62], fill=A(C["out"], .9 * al)); d.rectangle([x, y, x + 7, y + 62], fill=A(C["goldV"], al))
            stext(d, x + 26, y + 43, txt, f, A(C["ivory"], al), 1.7)

def draw_header(ov, t):
    d = ImageDraw.Draw(ov)
    # selo + capítulos + etiqueta
    o = k(t, .2, .6) * (1 - k(t, END0 - .4, END0))
    if o > 0 and SEL:
        f = font(26, 800); w = tlen(d, SEL, f, 2.6) + 44
        d.rounded_rectangle([90, 300, 90 + w, 356], 28, fill=A(C["gold"], o)); stext(d, 112, 338, SEL, f, A(C["navy"], o), 2.6)
        cur = -1
        for i, (lab, t0) in enumerate(CAPS):
            if t >= t0: cur = i
        for i in range(len(CAPS)):
            cx = 90 + w + 34 + i * 34
            if i <= cur: d.ellipse([cx - 11, 328 - 11, cx + 11, 328 + 11], fill=A(C["goldV"], o))
            else: d.ellipse([cx - 10, 318, cx + 10, 338], outline=A(C["gold"], o), width=3)
        if not CAPS: return
        s = CAPS[cur][0] if cur >= 0 else CAPS[0][0]; f2 = font(22, 700); w2 = tlen(d, s, f2, 2.2) + 50
        d.rounded_rectangle([90, 376, 90 + w2, 414], 4, fill=A(C["out"], .9 * o)); d.rectangle([104, 389, 116, 401], fill=A(C["goldV"], o)); stext(d, 126, 403, s, f2, A(C["ivory"], o), 2.2)

def draw_bottom(ov, t):
    d = ImageDraw.Draw(ov)
    n, gx, x0, x1 = 10, 10, 90, 900; sw = (x1 - x0 - gx * (n - 1)) / n; pr = t / TOTAL * n
    for i in range(n):
        fx = max(0, min(1, pr - i)); xa = x0 + i * (sw + gx)
        d.rounded_rectangle([xa, 236, xa + sw, 248], 2, fill=(35, 54, 79, 255))
        if fx > 0: d.rounded_rectangle([xa, 236, xa + sw * fx, 248], 2, fill=A(C["goldV"], 1))
    stext(d, 90, 284, "DIREITO FORA DOS AUTOS · @OHERMENEUTA_", font(22, 700), A(C["ivory"], .72), 3.3)
    d.rectangle([0, 0, W, 6], fill=A(C["gold"], 1))
    m = asset("meandro.png").copy(); a = np.asarray(m).copy(); a[:, :, 3] = (a[:, :, 3] * .55).astype(np.uint8); ov.alpha_composite(Image.fromarray(a), (0, 1462))

def draw_caption(ov, t):
    if t >= END0 - .2: return
    c = next((c for c in CH if c[0][1] - .05 <= t < c[-1][2] + .35), None)
    if not c: return
    d = ImageDraw.Draw(ov); size = 56; f = font(size, 700); sp = d.textlength(" ", font=f)
    allw = [dict(w=w[0], t0=w[1], t1=w[2], wd=d.textlength(w[0], font=f)) for w in c]; tot = sum(x["wd"] + sp for x in allw) - sp
    lines = [[]]
    if tot > 820:
        acc = 0
        for x in allw:
            if acc + x["wd"] > tot / 2 + 40 and lines[0] and len(lines) < 2: lines.append([])
            lines[-1].append(x); acc += x["wd"] + sp
    else: lines[0] = allw
    lh = 74; nL = len(lines); y0 = 1310 - (nL - 1) * lh / 2
    boxW = max(sum(x["wd"] + sp for x in l) - sp for l in lines) + 70
    d.rounded_rectangle([540 - boxW / 2, y0 - 58, 540 + boxW / 2, y0 - 58 + nL * lh + 30], 10, fill=A(C["out"], .9)); d.rectangle([540 - boxW / 2, y0 - 58 + nL * lh + 26, 540 + boxW / 2, y0 - 58 + nL * lh + 31], fill=A(C["goldV"], 1))
    pos = []
    for j, l in enumerate(lines):
        lw = sum(x["wd"] + sp for x in l) - sp; x = 540 - lw / 2
        for w in l: pos.append(dict(w=w, x=x, y=y0 + j * lh)); x += w["wd"] + sp
    vis = [p for p in pos if t >= p["w"]["t0"] - .02]; ci = len(vis) - 1
    mask = Image.new("L", (W, H), 0); md = ImageDraw.Draw(mask); hit = False
    if ci >= 0:
        cw = pos[ci]; pw = pos[ci - 1] if ci > 0 else None; mv = eout(k(t, cw["w"]["t0"] - .03, cw["w"]["t0"] + .13)); nxt = ci + 1 < len(pos)
        fade = 1 if nxt else 1 - k(t, cw["w"]["t1"] + .25, cw["w"]["t1"] + .45)
        if pw and pw["y"] == cw["y"]: xa = pw["x"] + (cw["x"] - pw["x"]) * mv; xb = pw["x"] + pw["w"]["wd"] + (cw["x"] + cw["w"]["wd"] - pw["x"] - pw["w"]["wd"]) * mv
        else: xa = cw["x"]; xb = cw["x"] + cw["w"]["wd"] * mv
        if fade > 0 and xb > xa + 1:
            a_, b_, top, bot = xa - 10, xb + 10, cw["y"] - 46, cw["y"] + 14
            poly = [(a_ + 4, top + 3), (b_, top), (b_ - 4, bot - 2), (a_, bot)]
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl); gd.polygon(poly, fill=A(C["goldV"], fade)); gd.line(poly + [poly[0]], fill=A(C["goldV"], fade), width=8, joint="curve")
            ov.alpha_composite(gl); md.polygon(poly, fill=255); hit = True
    for p in pos:
        if t >= p["w"]["t0"] - .02: d.text((p["x"], p["y"]), p["w"]["w"], font=f, fill=A(C["ivory"], 1), anchor="ls")
    if hit:
        dl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(dl)
        for p in pos:
            if t >= p["w"]["t0"] - .02: dd.text((p["x"], p["y"]), p["w"]["w"], font=f, fill=A(C["navy"], 1), anchor="ls")
        dl.putalpha(ImageChops.multiply(dl.getchannel("A"), mask)); ov.alpha_composite(dl)
    stext(d, 540 - d.textlength("ENCENAÇÃO ILUSTRATIVA", font=font(22, 700)) / 2 - 33, 1446, "ENCENAÇÃO ILUSTRATIVA", font(22, 700), A(C["ivory"], .6), 3.3) if False else None

def hand(ov, x, y, sc, rot=-12):
    s = 4
    L = Image.new("RGBA", (260 * s, 300 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    ox, oy = 90 * s, 20 * s
    def rr(x0, y0, x1, y1, r, fill): d.rounded_rectangle([ox + x0 * s, oy + y0 * s, ox + x1 * s, oy + y1 * s], r * s, fill=fill, outline=(10, 22, 38, 255), width=5 * s // 2)
    fill = A(C["ivory"], 1)
    rr(-6, 0, 18, 70, 10, fill)         # indicador
    rr(-12, 54, 94, 138, 28, fill)       # palma
    for i, (a, b) in enumerate(((18, 62), (40, 66), (58, 70))): rr(a, 44 - i * 0, a + 18, b + 12, 9, fill)
    rr(-30, 66, -6, 108, 12, fill)       # polegar
    L = L.resize((260, 300), Image.LANCZOS); L = L.rotate(rot, expand=True, resample=Image.BICUBIC, center=(90, 20))
    L = L.resize((int(L.width * sc), int(L.height * sc)), Image.LANCZOS)
    ov.alpha_composite(L, (int(x - 90 * sc), int(y - 20 * sc))) if x - 90 * sc >= 0 and y - 20 * sc >= 0 else ov.paste(L, (int(x - 90 * sc), int(y - 20 * sc)), L)

def endcard(t):
    ts = END0; p = eout(k(t, ts, ts + .45)); im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bg = np.zeros((H, W, 3), np.float32); yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(0, 1, W)[None, :]; g = (xx * W + yy * H) / (W + H)
    for ch in range(3): bg[:, :, ch] = C["navy"][ch] + (C["base"][ch] - C["navy"][ch]) * g
    base = Image.fromarray(bg.astype(np.uint8)).convert("RGBA"); hero = asset("hero-hermeneuta.png").copy()
    fade = np.zeros((430, 1), np.float32); ys = np.linspace(0, 1, 430); fade[:, 0] = np.clip((ys - .6) / .4, 0, 1)
    ha = np.asarray(hero).astype(np.float32); ha[:, :, :3] = ha[:, :, :3] * (1 - fade[:, :, None]) + np.array(C["navy"], np.float32) * fade[:, :, None]
    base.paste(Image.fromarray(ha.astype(np.uint8)), (0, 310)); d = ImageDraw.Draw(base)
    a = k(t, ts + .2, ts + .6)
    if a > 0:
        stext(d, 90, 812, "LANÇAMENTO" if not JA else "NO AR", font(32, 800), A(C["gold2"], a), 7); d.line([380, 801, 500, 801], fill=A(C["gold2"], a), width=3)
    cb = pop(t, ts + .35)
    if cb > 0:
        cal = Image.new("RGBA", (300, 360), (0, 0, 0, 0)); cd = ImageDraw.Draw(cal); cd.rectangle([75, 90, 225, 270], fill=A(C["ivory"], 1)); cd.rectangle([75, 90, 225, 132], fill=A(C["gold"], 1))
        stext(cd, 150 - (tlen(cd, MES, font(28, 800), 5) - 5) / 2, 120, MES, font(28, 800), A(C["navy"], 1), 5); cd.text((150, 152 + 62 - 8), "17", font=geo(96), fill=A(C["navy"], 1), anchor="ms") if False else cd.text((150, 242), DIA, font=geo(96), fill=A(C["navy"], 1), anchor="ms")
        cal = cal.resize((int(300 * cb), int(360 * cb)), Image.LANCZOS); base.alpha_composite(cal, (int(175 - 150 * cb), int(960 - 180 * cb))) if 175 - 150 * cb >= 0 else None
    b2 = k(t, ts + .5, ts + .9)
    if b2 > 0:
        gf = geo(66); gi = geo(66, True); d.text((290, 940), "Dia ", font=gf, fill=A(C["ivory"], b2), anchor="ls"); d.text((290 + d.textlength("Dia ", font=gf), 940), LANC, font=gi, fill=A(C["gold2"], b2), anchor="ls")
        d.text((290, 1018), "o site estreia." if not JA else "o site já está no ar.", font=gf, fill=A(C["ivory"], b2), anchor="ls")
    c2 = pop(t, ts + .7)
    if c2 > 0:
        pr = Image.new("RGBA", (920, 160), (0, 0, 0, 0)); pd = ImageDraw.Draw(pr); pd.rounded_rectangle([5, 6, 915, 154], 6, fill=(255, 255, 255, 18), outline=A(C["b4"], 1), width=2)
        av = asset("avatar-hermeneuta.png").resize((108, 108), Image.LANCZOS); pr.alpha_composite(av, (35, 26))
        stext(pd, 170, 74, "ohermeneuta_", font(42, 700), A((248, 246, 242), 1)); stext(pd, 170, 118, "O Hermeneuta · Direito e cultura", font(28, 400), (184, 194, 208, 255))
        tc = CLICK
        if t < tc: pressed = 1 - .08 * math.sin(math.pi * k(t, tc - .12, tc)); bw, bh = int(240 * pressed), int(68 * pressed)
        else: pressed = 1 + .12 * math.sin(math.pi * k(t, tc, tc + .3)); bw, bh = int(240 * pressed), int(68 * pressed)
        bx, by = 460 + 270 - 450 + 450 - 5, 80
        cx, cy = 730, 80
        if t < tc:
            pd.rounded_rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2], 8, fill=A(C["goldV"], 1)); pd.text((cx, cy + 12), "Seguir", font=font(34, 800), fill=A(C["navy"], 1), anchor="ms")
        else:
            pd.rounded_rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2], 8, fill=(35, 54, 79, 255), outline=A(C["b4"], 1), width=3)
            pd.line([(cx - 84, cy), (cx - 74, cy + 10), (cx - 56, cy - 10)], fill=A(C["goldV"], 1), width=6, joint="curve"); pd.text((cx + 14, cy + 12), "Seguindo", font=font(32, 800), fill=A(C["ivory"], 1), anchor="ms")
        sc = c2; pr = pr.resize((int(920 * sc), int(160 * sc)), Image.LANCZOS); base.alpha_composite(pr, (int(540 - 460 * sc), int(1130 - 80 * sc)))
    # clique: mão
    tc = CLICK; bx0, by0 = 810, 1130
    if tc - .9 <= t <= tc + 1.1:
        ent = eout(k(t, tc - .9, tc - .2)); sai = eio(k(t, tc + .5, tc + 1.1))
        x = 1010 + (bx0 + 4 - 1010) * ent + sai * 220; y = 1560 + (by0 + 8 - 1560) * ent + sai * 380
        if t > tc:
            r = k(t, tc, tc + .5); ring = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([bx0 - 30 - r * 110, by0 - 30 - r * 110, bx0 + 30 + r * 110, by0 + 30 + r * 110], outline=A(C["goldV"], 1 - r), width=max(1, int(8 * (1 - r)))); base.alpha_composite(ring)
        pr_ = 1 - .14 * math.sin(math.pi * k(t, tc - .12, tc + .1)); hand(base, x, y, pr_ * .9)
    # desliza de baixo para cima
    off = int((1 - p) * H); im.alpha_composite(base.crop((0, 0, W, H - off)) if off < H else base.crop((0, 0, 1, 1)), (0, off)) if off < H else None
    return im

def overlay(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t >= END0:
        e = endcard(t); ov.alpha_composite(e)
    else:
        draw_header(ov, t); draw_labels(ov, t); draw_caption(ov, t)
        if ROTULO:
            d = ImageDraw.Draw(ov); f = font(22, 700); stext(d, 540 - (tlen(d, ROTULO, f, 3.3) - 3.3) / 2, 1440, ROTULO, f, A(C["ivory"], .62), 3.3)
    draw_bottom(ov, t)
    return ov
