# Formato "NA FONTE": percorre a página real da notícia/julgado, grifa os trechos falados, com margem explicativa, escada de números, glossário e selo de fonte.
# Uso (cwd = pasta do reel): python nafonte.py [segundos_de_teste ...]   | sem argumentos renderiza saida/<nome>.mp4
# Precisa: roteiro.json, tempos.json, align.json, audio.wav, page.png + rects.json (capture.mjs), nafonte.json
import sys, os, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
import words, ui
from ui import font, geo, C, A, eout, eio, tlen, stext, k as kk
W, H = 1080, 1920; WX, WY, WW, WH = 40, 440, 1000, 560; MY0, MY1 = 1025, 1222
CWW, NOTA_Y0, NOTA_LH = WW, 104, 48
R = words.R; TM = json.load(open("tempos.json")); SENT = TM["sent"]; END0 = TM["END0"]; TOTAL = TM["TOTAL"]
CFG = json.load(open("nafonte.json")); RC = json.load(open("rects.json")); DSF = RC["dsf"]
if CFG.get("layout") == "pessoa_dir":   # apresentador à direita, fora da coluna de botões do Instagram (x>950) e da faixa de baixo (y>1570)
    CWW, MY1, NOTA_Y0, NOTA_LH = 545, 1262, 98, 44
    ui.CAP.update(cx=WX + 272, y=1390, w=460, fs=50); ui.MEANDRO = False
PG = cv2.imread(CFG.get("pagina", "page.png")); PH, PW = PG.shape[:2]
PYR = {1.0: PG, .5: cv2.resize(PG, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA), .25: cv2.resize(PG, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA)}
# ---------- tempos das palavras por frase
SW = {}
for w, a, b, i in words.WORDS: SW.setdefault(i, []).append((a, b))
def span(si, f=None, t=None):
    ws = SW[si]; a = ws[0 if f is None else f][0]; b = ws[-1 if t is None else t][1]
    return (a, b) if f is not None else (SENT[si][0] + .05, SENT[si][1] - .05)
def tok(si, i): return SW[si][i]
# ---------- varreduras (grifos)
def lines_of(name): return [[v * DSF for v in l] for l in RC["rects"][name]]
SWEEPS = []
for s in CFG["sweeps"]:
    ln = lines_of(s["rect"]); ta, tb = span(s["sent"], s.get("from"), s.get("to"))
    if s.get("at") is not None: ta = tok(s["sent"], s["at"])[0]; tb = ta + s.get("dur", .6)
    SWEEPS.append(dict(id=s["id"], lines=ln, ta=ta, tb=tb, beat=s["sent"], mark=s.get("mark", True), zoom=s.get("zoom"), pan=s.get("pan")))
def prog(sw, t):
    tot = sum(l[2] - l[0] for l in sw["lines"]); p = min(1, max(0, (t - sw["ta"]) / max(.05, sw["tb"] - sw["ta"]))) * tot; out = []; head = None
    for l in sw["lines"]:
        w = l[2] - l[0]; f = min(1, max(0, p / w)); p -= w; out.append((l, f))
        if f > 0: head = (l[0] + w * f, (l[1] + l[3]) / 2)
    return out, head
# ---------- câmera: zoom fixo (a coluna inteira cabe na janela), sem pan horizontal; só desce a página, com glides longos e suaves
COLX = (RC["root"][0] + RC["root"][2]) / 2 * DSF
S_TXT = min(CFG.get("zoom", 9), (WW - 40) / ((RC["root"][2] - RC["root"][0]) * DSF + 20))
def clampc(x, y, s):
    hx, hy = WW / 2 / s, WH / 2 / s; lo, hi = RC["root"][0] * DSF + hx - 20, RC["root"][2] * DSF - hx + 20
    x = COLX if s <= S_TXT + 1e-3 or lo >= hi else min(max(x, lo), hi)
    return x, min(max(y, hy), PH - hy)
def keys():
    # zoom padrão: coluna inteira, só rolagem vertical. Varredura com "zoom" > padrão: aproxima e acompanha o grifo de lado, devagar.
    sw_all = sorted(SWEEPS, key=lambda q: q["ta"]); q0 = sw_all[0]
    cur = (COLX, clampc(0, (q0["lines"][0][1] + q0["lines"][-1][3]) / 2, S_TXT)[1], S_TXT); pts = [(0.0,) + cur]; prev_tb = CFG.get("cam_t0", 0.0)
    thr = CFG.get("move_thr", .22) * WH / S_TXT
    def glide(a, b, t_end):
        dist = math.hypot(b[0] - a[0], b[1] - a[1]) * b[2] + abs(math.log(b[2] / a[2])) * 900
        dur = min(CFG.get("glide_max", 1.8), max(CFG.get("glide_min", .9), .7 + dist / 2500)); st = max(prev_tb + .05, t_end - dur)
        pts.append((st,) + a)
        for i in range(1, 13):
            u = i / 12; e = u * u * (3 - 2 * u); pts.append((st + dur * u, a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * e)))
        return st + dur
    for q in sw_all:
        z = q.get("zoom") or S_TXT
        if z <= S_TXT + 1e-3:
            tgt = (COLX, clampc(0, (q["lines"][0][1] + q["lines"][-1][3]) / 2, S_TXT)[1], S_TXT)
            if abs(tgt[1] - cur[1]) > thr or abs(cur[2] - S_TXT) > .01 or abs(cur[0] - COLX) > 5: glide(cur, tgt, q["ta"] - .1); cur = tgt
        else:
            hx = WW / 2 / z
            if q.get("pan") is False:   # lupa parada: zoom fixo, alinhado ao início das linhas, sem vai e vem lateral
                tgt = (*clampc(min(l[0] for l in q["lines"]) + hx - 40, (q["lines"][0][1] + q["lines"][-1][3]) / 2, z), z)
                if abs(tgt[1] - cur[1]) > thr * .5 or abs(tgt[0] - cur[0]) > 30 or abs(math.log(cur[2] / z)) > .02: glide(cur, tgt, q["ta"] - .1); cur = tgt
                prev_tb = max(prev_tb, q["tb"]); continue
            path = []; tot = sum(l[2] - l[0] for l in q["lines"]); cum = 0
            for l in q["lines"]:
                ti = q["ta"] + (q["tb"] - q["ta"]) * cum / tot; cum += l[2] - l[0]; to_ = q["ta"] + (q["tb"] - q["ta"]) * cum / tot
                yl = (l[1] + l[3]) / 2; c0 = l[0] + hx - 40; c1 = l[2] - hx + 40
                if c1 <= c0: c0 = c1 = (l[0] + l[2]) / 2
                p0 = clampc(c0, yl, z); p1 = clampc(c1, yl, z)
                path.append((ti + .1, p0[0], p0[1], z)); path.append((max(ti + .15, to_ - .1), p1[0], p1[1], z))
            if not path: continue
            ten = glide(cur, path[0][1:], q["ta"] + .05)
            for p in path:
                if p[0] > ten: pts.append(p)
            cur = path[-1][1:]
            if CFG.get("volta_inicio", True):   # depois do grifo com lupa, volta devagar para o início da linha (texto lido da esquerda)
                back = (*clampc(q["lines"][0][0] * 0 + min(l[0] for l in q["lines"]) + hx - 40, cur[1], z), z)
                for i in range(1, 9):
                    u = i / 8; e = u * u * (3 - 2 * u); pts.append((q["tb"] + .15 + .9 * u, cur[0] + (back[0] - cur[0]) * e, cur[1], z))
                cur = back; prev_tb = max(prev_tb, q["tb"] + 1.05)
        prev_tb = max(prev_tb, q["tb"])
    pts.append((TOTAL + 1,) + cur); pts.sort(key=lambda z: z[0]); return pts
def cam_track():
    ks = keys(); T = np.arange(0, TOTAL + 1, 1 / 120); K = np.array(ks)
    x = np.interp(T, K[:, 0], K[:, 1]); y = np.interp(T, K[:, 0], K[:, 2]); ls = np.interp(T, K[:, 0], np.log(K[:, 3]))
    sg = int(CFG.get("cam_sigma", .18) * 120); g = np.exp(-.5 * (np.arange(-3 * sg, 3 * sg + 1) / sg) ** 2); g /= g.sum()
    sm = lambda a: np.convolve(np.pad(a, (3 * sg, 3 * sg), mode="edge"), g, mode="valid")
    return T, sm(x), sm(y), np.exp(sm(ls))
CT, CX, CY, CS = cam_track()
def cam(t):
    i = min(len(CT) - 1, int(t * 120)); j = max(0, i - 6); return CX[i], CY[i], CS[i], (CY[i] - CY[j]) * CS[i] * 20   # vy em px de vídeo/s
# ---------- janela do documento
RM = np.zeros((WH, WW), np.float32); _m = Image.new("L", (WW * 2, WH * 2), 0); ImageDraw.Draw(_m).rounded_rectangle([0, 0, WW * 2 - 1, WH * 2 - 1], 36, fill=255); RM = np.asarray(_m.resize((WW, WH), Image.LANCZOS), np.float32)[..., None] / 255
GOLD_MUL = np.array([.36, .84, 1.0], np.float32)
def window(t):
    cx, cy, s, vy = cam(t); lv = 1.0 if s >= .7 else .5 if s >= .35 else .25; img = PYR[lv]; r = s / lv
    M = np.array([[r, 0, WW / 2 - cx * lv * r], [0, r, WH / 2 - cy * lv * r]], np.float32)
    w = cv2.warpAffine(img, M, (WW, WH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    if abs(vy) > 700:
        kl = int(min(61, abs(vy) / 45)) | 1; ker = np.zeros((kl, kl), np.float32); ker[:, kl // 2] = 1 / kl; w = cv2.filter2D(w, -1, ker)
    to = lambda x, y: ((x - cx) * s + WW / 2, (y - cy) * s + WH / 2)
    # holofote: escurece fora do trecho do capítulo corrente
    wt = 0.0; band = None
    for si in range(len(SENT)):
        mine = [q for q in SWEEPS if q["beat"] == si]
        if not mine: continue
        a, b = SENT[si][0] - .1, SENT[si][1] + .35; v = min(kk(t, a, a + .3), 1 - kk(t, b - .3, b))
        if v > wt: wt = v; y0 = min(l[1] for q in mine for l in q["lines"]); y1 = max(l[3] for q in mine for l in q["lines"]); band = (y0, y1)
    if band and wt > 0 and CFG.get("dim", .5) > 0:
        ys = (np.arange(WH, dtype=np.float32) - WH / 2) / s + cy; m = np.clip(1 - np.maximum(band[0] - 60 - ys, ys - band[1] - 60) / 90, 0, 1)
        w *= (1 - CFG.get("dim", .5) * wt * (1 - m))[:, None, None]
    for sw in SWEEPS:
        if t < sw["ta"] - .02 or not sw["mark"]: continue
        parts, head = prog(sw, t)
        for l, f in parts:
            if f <= 0: continue
            x0, y0 = to(l[0] - 5, l[1] - 3); x1, y1 = to(l[0] - 5 + (l[2] - l[0] + 10) * f, l[3] + 3)
            xa, xb, ya, yb = int(max(0, x0)), int(min(WW, x1)), int(max(0, y0)), int(min(WH, y1))
            if xb > xa and yb > ya: w[ya:yb, xa:xb] *= GOLD_MUL; w[max(ya, yb - 3):yb, xa:xb] = (np.array([75, 162, 201], np.float32) * .9 + w[max(ya, yb - 3):yb, xa:xb] * .1)
    w *= (1 - .18 * (1 - np.clip(1 - (((np.arange(WW) - WW / 2) / (WW / 2)) ** 2)[None, :, None] * .6, 0, 1)))
    return w[..., ::-1]   # RGB
def bgcanvas():
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]; a = np.array(C["navy"], np.float32); b = np.array(C["base"], np.float32)
    g = a + (b - a) * (np.clip(y * 1.3 - .15, 0, 1)) * .55; g = np.repeat(g, W, 1)
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle([WX - 4, WY + 10, WX + WW + 4, WY + WH + 18], 40, fill=150); sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(18)), np.float32)[..., None] / 255
    return g * (1 - sh * .6)
BG = bgcanvas()
# ---------- elementos gráficos
def pill(d, x, y, txt, f, fill, fg, ls=1.6, pad=22, h=44, r=10, border=None):
    w = tlen(d, txt, f, ls) + pad * 2; d.rounded_rectangle([x, y, x + w, y + h], r, fill=fill, outline=border, width=3 if border else 0); stext(d, x + pad, y + h - 13, txt, f, fg, ls); return w
def check(d, x, y, sz, col):
    d.line([(x, y + sz * .55), (x + sz * .38, y + sz * .9), (x + sz, y + sz * .12)], fill=col, width=max(4, int(sz * .2)), joint="curve")
def cross(d, x, y, sz, col):
    d.line([(x, y), (x + sz, y + sz)], fill=col, width=max(4, int(sz * .2))); d.line([(x + sz, y), (x, y + sz)], fill=col, width=max(4, int(sz * .2)))
def back(t0, d=.4): return lambda t: ui.pop(t, t0, d)
def chip_layer(im, t):
    d = ImageDraw.Draw(im, "RGBA")
    for c in CFG["chips"]:
        sn = c.get("sent_to", c["sent"]); a, b = (max(SENT[c["sent"]][0] - .1, c.get("t0", 0)), (SENT[sn + 1][0] if sn + 1 < len(SENT) else END0) - .02)
        if not (a <= t < b): continue
        o = min(kk(t, a, a + .25), 1 - kk(t, b - .2, b)); f = font(25, 800); x = WX + 18 + int((1 - eout(kk(t, a, a + .3))) * -30); y = WY + WH - 34
        no = c.get("tipo") == "no"; txt = c["texto"]; w = tlen(d, txt, f, 2) + 84
        d.rounded_rectangle([x, y, x + w, y + 50], 25, fill=A(C["navy"], .96 * o), outline=A((214, 80, 80) if no else C["goldV"], o), width=3)
        (cross if no else check)(d, x + 20, y + 14, 22, A((236, 96, 96) if no else C["goldV"], o)); stext(d, x + 56, y + 34, txt, f, A(C["ivory"], o), 2)
def card_frame(d, o, label, col=None):
    d.rounded_rectangle([WX, MY0, WX + CWW, MY1], 18, fill=A(C["out"], .93 * o)); d.rectangle([WX, MY0 + 14, WX + 8, MY1 - 14], fill=A(col or C["goldV"], o))
    stext(d, WX + 36, MY0 + 42, label, font(23, 800), A(col or C["gold2"], o), 3)
def wrap(d, txt, f, wmax):
    ws = txt.split(); ls = []; cur = ""
    for w_ in ws:
        tr = (cur + " " + w_).strip()
        if d.textlength(tr, font=f) <= wmax: cur = tr
        else: ls.append(cur); cur = w_
    ls.append(cur); return ls
def cards_layer(im, t):
    d = ImageDraw.Draw(im, "RGBA")
    for c in CFG["cards"]:
        a = (tok(c["sent"], c["from"])[0] if c.get("from") is not None else SENT[c["sent"]][0]) + c.get("off", 0)
        se = c.get("sent_to", c["sent"]); b = (tok(se, c["to"])[1] if c.get("to") is not None else (SENT[se + 1][0] if se + 1 < len(SENT) else END0)) + c.get("offb", -.02)
        if not (a - .01 <= t < b): continue
        o = min(kk(t, a, a + .25), 1 - kk(t, b - .22, b)); dy = int((1 - eout(kk(t, a, a + .35))) * 22)
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(tmp, "RGBA")
        if c["tipo"] == "nota":
            card_frame(td, 1, c["label"]); f = font(c.get("fs", 39), 700); ls = wrap(td, c["texto"], f, CWW - 72)
            for i, l in enumerate(ls): stext(td, WX + 36, MY0 + NOTA_Y0 + i * NOTA_LH, l, f, A(C["ivory"], 1))
        elif c["tipo"] == "glossario":
            card_frame(td, 1, c["label"], (150, 190, 240)); f = font(c.get("fs", 35), 600); ls = wrap(td, c["texto"], f, WW - 80)
            for i, l in enumerate(ls): stext(td, WX + 36, MY0 + 96 + i * 43, l, f, A(C["ivory"], 1))
            stext(td, WX + WW - 36 - tlen(td, c["credito"], font(21, 700), 2), MY1 - 14, c["credito"], font(21, 700), A((150, 190, 240), .9), 2) if c.get("credito") else None
        elif c["tipo"] == "escada":
            card_frame(td, 1, c["label"]); cols = c["cols"]; rows = c["rows"]; x0 = WX + 196; cw = 250; gap = 32; f = font(28, 800); fs_ = font(21, 800)
            for j, hd in enumerate(cols): stext(td, x0 + j * (cw + gap), MY0 + 78, hd["nome"], fs_, A(C["ivory"], .75), 2.2)
            for r, row in enumerate(rows):
                y = MY0 + 92 + r * 52; stext(td, WX + 36, y + 35, row["nome"], font(22, 800), A(C["ivory"], .8), 1.4)
                for j, v in enumerate(row["v"]):
                    ta_ = tok(c["sent"], cols[j]["tok_r"][r])[0] if cols[j].get("tok_r") else SENT[c["sent"]][0] + .15 + j * .0
                    pp = ui.pop(t, ta_ - c.get("lead", 0) - a + a if False else ta_, .4); 
                    if pp <= 0: continue
                    x = x0 + j * (cw + gap); last = j == len(cols) - 1; sc = .8 + .2 * min(pp, 1.15)
                    fill = A(C["goldV"], 1) if last else A((52, 86, 130), 1); fg = C["navy"] if last else C["ivory"]; wchip = int(cw * sc)
                    td.rounded_rectangle([x, y, x + wchip, y + 44], 10, fill=fill); ww_ = tlen(td, v, f, 0); stext(td, x + (wchip - ww_) / 2, y + 32, v, f, A(fg, 1))
                    if j == 1 and cols[2].get("tok_r") and t >= tok(c["sent"], cols[2]["tok_r"][r])[0] - .05: td.line([(x + 14, y + 22), (x + wchip - 14, y + 22)], fill=A((236, 96, 96), 1), width=5)
                    if j < len(cols) - 1: td.polygon([(x + cw + 8, y + 12), (x + cw + 28, y + 22), (x + cw + 8, y + 32)], fill=A(C["gold"], .9))
            tg = c.get("tag")
            if tg and t >= tok(c["sent"], tg["tok"])[0]: pill(td, WX + WW - 36 - (tlen(td, tg["texto"], font(21, 800), 2) + 44), MY0 + 20, tg["texto"], font(21, 800), A(C["goldV"], 1), C["navy"], 2, 22, 36, 8)
        elif c["tipo"] == "linha":      # linha do tempo: itens [{data, texto, tok}] surgem quando a palavra tok é falada
            card_frame(td, 1, c["label"]); it = c["itens"]; n = len(it); x0 = WX + 140; x1 = WX + WW - 140; yl = MY0 + 108
            td.line([(x0, yl), (x1, yl)], fill=A(C["ivory"], .35), width=4)
            for j, q in enumerate(it):
                tq = tok(c["sent"], q["tok"])[0] if q.get("tok") is not None else SENT[c["sent"]][0] + .2 + j * .5; pp = ui.pop(t, tq, .4)
                if pp <= 0: continue
                x = x0 + (x1 - x0) * (j / max(1, n - 1) if n > 1 else .5); last = j == n - 1; r = 11 * min(pp, 1.15)
                td.ellipse([x - r, yl - r, x + r, yl + r], fill=A(C["goldV"] if last else C["ivory"], 1)); fd = font(30, 900); fx = font(22, 700)
                stext(td, x - tlen(td, q["data"], fd, 1) / 2, yl - 22, q["data"], fd, A(C["goldV"] if last else C["ivory"], 1), 1)
                for k_, l_ in enumerate(wrap(td, q["texto"], fx, min(250, (x1 - x0) / max(1, n - 1) - 14) if n > 1 else 400)[:2]): stext(td, x - tlen(td, l_, fx) / 2, yl + 42 + k_ * 26, l_, fx, A(C["ivory"], .9))
        elif c["tipo"] == "votos":      # quadro de votos: linhas [{nome, voto, vencedor:bool, tok}]
            card_frame(td, 1, c["label"]); fn = font(26, 800); fv = font(24, 600)
            for j, q in enumerate(c["linhas"][:3]):
                tq = tok(c["sent"], q["tok"])[0] if q.get("tok") is not None else SENT[c["sent"]][0] + .2 + j * .6
                if t < tq: continue
                y = MY0 + 70 + j * 42; win = q.get("vencedor", False); col = C["goldV"] if win else (150, 160, 175)
                pill(td, WX + 36, y, "PREVALECEU" if win else "VENCIDO", font(18, 900), A(col, 1), C["navy"], 1.5, 12, 32, 7)
                stext(td, WX + 210, y + 24, q["nome"], fn, A(C["ivory"], 1)); stext(td, WX + 210 + tlen(td, q["nome"], fn) + 18, y + 24, q["voto"], fv, A(C["ivory"], .75))
        elif c["tipo"] == "dossie":     # dossiê: miniaturas de outros documentos oficiais [{img, rotulo, tok}]
            card_frame(td, 1, c["label"]); docs = c["docs"][:3]; tw = 200; th = 96
            for j, q in enumerate(docs):
                tq = tok(c["sent"], q["tok"])[0] if q.get("tok") is not None else SENT[c["sent"]][0] + .2 + j * .5; pp = ui.pop(t, tq, .4)
                if pp <= 0: continue
                im_ = Image.open(q["img"]).convert("RGB"); im_ = im_.crop((0, 0, im_.width, int(im_.width * th / tw))).resize((tw, th), Image.LANCZOS)
                x = WX + 36 + j * (tw + 40); y = MY0 + 62; td.rectangle([x - 4, y - 4, x + tw + 4, y + th + 4], fill=A(C["ivory"], 1)); tmp.paste(im_, (x, y))
                stext(td, x, y + th + 24, q["rotulo"], font(19, 800), A(C["gold2"], 1), 1.5)
        al = tmp.getchannel("A").point(lambda v: int(v * o)); tmp.putalpha(al); im.alpha_composite(tmp, (0, -dy if False else dy))
def stamp_layer(im, t):
    for s in CFG.get("carimbos", []):
        a = SENT[s["sent"]][0] + s.get("off", .35); b = (SENT[s["sent"] + 1][0] if s["sent"] + 1 < len(SENT) else END0)
        if not (a <= t < b): continue
        x = kk(t, a, a + .22); sc = 1 + 1.4 * (1 - eout(x)) ; o = min(x * 1.6, 1) * (1 - kk(t, b - .25, b)); rot = -7
        lay = Image.new("RGBA", (880, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); col = (225, 78, 78)
        d.rounded_rectangle([6, 6, 874, 254], 22, outline=A(col, 1), width=10); d.rounded_rectangle([26, 26, 854, 234], 12, outline=A(col, .8), width=3)
        f1 = font(74, 900); t1 = s["texto"]; stext(d, 440 - (tlen(d, t1, f1, 2) - 2) / 2, 128, t1, f1, A(col, 1), 2); f2 = font(40, 800); stext(d, 440 - (tlen(d, s["sub"], f2, 3) - 3) / 2, 200, s["sub"], f2, A(col, .95), 3)
        sw, sh_ = int(lay.width * sc * .95), int(lay.height * sc * .95); lay = lay.resize((sw, sh_), Image.LANCZOS).rotate(rot, expand=True, resample=Image.BICUBIC)
        a_ = lay.getchannel("A").point(lambda v: int(v * o * .96)); lay.putalpha(a_)
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").point(lambda v: int(v * .35)))
        cxs, cys = WX + WW // 2, WY + WH // 2 - 6; im.alpha_composite(lay, (cxs - lay.width // 2, cys - lay.height // 2))
def frame_main(t):
    base = BG.copy(); w = window(t); base[WY:WY + WH, WX:WX + WW] = base[WY:WY + WH, WX:WX + WW] * (1 - RM) + w * RM
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im); d.rounded_rectangle([WX, WY, WX + WW, WY + WH], 36, outline=A(C["gold"], 1), width=3)
    cx_, cy_, s_, _ = cam(t); tr0, tr1 = WY + 26, WY + WH - 26; th = max(40, (tr1 - tr0) * (WH / s_) / PH); ty = tr0 + (tr1 - tr0 - th) * min(1, max(0, (cy_ - WH / 2 / s_) / max(1, PH - WH / s_)))
    d.rounded_rectangle([WX + WW - 16, tr0, WX + WW - 8, tr1], 4, fill=A(C['ivory'], .18)); d.rounded_rectangle([WX + WW - 16, ty, WX + WW - 8, ty + th], 4, fill=A(C['goldV'], .95))
    if t < END0:
        chip_layer(im, t); cards_layer(im, t); stamp_layer(im, t)
        dd = CFG.get("dim_end", .0)
    return im
AB = None
if CFG.get("abertura"):
    import abertura_pasta; AB = abertura_pasta.Pasta(CFG["abertura"], PG, DSF, font); T_AB = CFG["abertura"]["t_fim"]
def frame(t):
    if AB and t < T_AB:
        img = AB.frame(t); x = kk(t, T_AB - .3, T_AB)
        if x > 0: img = img * (1 - x) + np.asarray(frame_main(t).convert("RGB"), np.float32) * x
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        hd = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ui.draw_header(hd, t); hd.putalpha(hd.getchannel("A").point(lambda v: int(v * kk(t, T_AB - .6, T_AB))))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ui.draw_caption(ov, t); im.alpha_composite(hd); im.alpha_composite(ov); return im.convert("RGB")
    im = frame_main(t)
    if PES and INTRO and t < INTRO["fim"] + INTRO.get("transicao", .7):
        intro_layer(im, t); im.alpha_composite(ui.overlay(t)); return im.convert("RGB")
    im.alpha_composite(ui.overlay(t)); pessoa_layer(im, t); return im.convert("RGB")
PES = CFG.get("pessoa"); INTRO = CFG.get("intro"); _rd = {}
def mov_frame(arq, i):
    pj = json.load(open(os.path.splitext(arq)[0] + ".json")); w, h = pj["w"], pj["h"]; r = _rd.get(arq)
    if r is None or i != r[1] + 1:
        if r is not None: r[0].kill()
        r = [subprocess.Popen(["ffmpeg", "-v", "error", "-ss", "%.3f" % (i / 30), "-i", arq, "-f", "rawvideo", "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE), i - 1]; _rd[arq] = r
    b = r[0].stdout.read(w * h * 4); r[1] = i
    return Image.frombytes("RGBA", (w, h), b) if len(b) == w * h * 4 else None
def pessoa_frame(i): return mov_frame(PES["arquivo"], i)
def fade_base(p, n=70):   # base do busto se dissolve (não termina num corte reto)
    a = np.asarray(p.getchannel("A"), np.float32); a[-n:] *= np.linspace(1, 0, n)[:, None]; p.putalpha(Image.fromarray(a.astype(np.uint8))); return p
def rect_small(pw, ph):
    if PES.get("lado", "esq") == "dir":
        yb = PES.get("y_base", 1570); return (W - PES.get("x", 135) - pw, yb - ph, pw, ph)
    return (PES.get("x", 8), H - ph + PES.get("dy", 0), pw, ph)
def stamp_img():
    if "_st" in globals(): return globals()["_st"]
    l1, l2 = INTRO.get("carimbo", ["VAI CAIR", "NA TUA PROVA"]); w, h = 860, 300; red = (186, 24, 30)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, w - 7, h - 7], 26, outline=red + (255,), width=12); d.rounded_rectangle([26, 26, w - 27, h - 27], 16, outline=red + (255,), width=4)
    for sz in range(130, 40, -2):
        f2 = font(sz, 900)
        if d.textlength(l2, font=f2) < w - 110: break
    f1 = font(int(sz * .92), 900)
    d.text((w / 2, h * .40), l1, font=f1, fill=red + (255,), anchor="mm"); d.text((w / 2, h * .74), l2, font=f2, fill=red + (255,), anchor="mm")
    a = np.asarray(im).astype(np.float32); g = np.random.default_rng(5)
    import cv2 as _cv
    nz = _cv.GaussianBlur(g.random((h, w)).astype(np.float32), (0, 0), 2.0); nz = (nz - nz.min()) / (nz.max() - nz.min())
    a[..., 3] *= np.clip(.62 + nz * .6, 0, 1) * (g.random((h, w)) > .03)
    out = Image.fromarray(a.astype(np.uint8)).rotate(INTRO.get("rot", 7), expand=True, resample=Image.BICUBIC); globals()["_st"] = out; return out
def intro_layer(im, t):
    """abertura: apresentador grande no centro, carimbo vermelho; no fim encolhe para o canto. Devolve True se cuidou da pessoa."""
    t1 = INTRO["fim"]; tr = INTRO.get("transicao", .7)
    if t >= t1 + tr: return False
    u = eio(kk(t, t1, t1 + tr))
    # escurece a página enquanto ele está grande
    dk = Image.new("RGBA", (W, H), (8, 18, 32, int(150 * (1 - u)))); im.alpha_composite(dk)
    pb = mov_frame(INTRO["grande"], int(round(t * 30)))
    if pb is not None:
        bw, bh = pb.size; big = ((W - bw) // 2, INTRO.get("y_base", 1570) - bh, bw, bh)
        ps = json.load(open(os.path.splitext(PES["arquivo"])[0] + ".json")); e_ = PES.get("escala", 1); sm = rect_small(int(ps["w"] * e_), int(ps["h"] * e_))
        x, y, w_, h_ = [big[k] + (sm[k] - big[k]) * u for k in range(4)]
        p = fade_base(pb.resize((max(2, int(w_)), max(2, int(h_))), Image.LANCZOS), int(70 * h_ / bh) + 1)
        im.alpha_composite(p, (int(x), int(y)))
    # carimbo
    tc = INTRO.get("t_carimbo", .45); ta = tc - .24
    if t >= ta:
        st = stamp_img(); v = min(1, (t - ta) / .24); sc = 1 + 1.4 * (1 - eout(v)); al = min(1, v * 2.2) * (1 - kk(t, t1 - .1, t1 + .35))
        if al > 0:
            s_ = st.resize((int(st.width * sc * .9), int(st.height * sc * .9)), Image.BICUBIC)
            if al < 1: s_.putalpha(s_.getchannel("A").point(lambda q: int(q * al)))
            cx, cy = INTRO.get("carimbo_xy", (540, 560)); shake = int(math.exp(-(t - tc) * 16) * math.sin((t - tc) * 75) * 14) if t >= tc else 0
            im.alpha_composite(s_, (int(cx - s_.width / 2) + shake, int(cy - s_.height / 2) + shake // 2))
    return True
def pessoa_layer(im, t):
    if not PES or t >= END0: return
    if INTRO and intro_layer(im, t): return
    p = pessoa_frame(int(round(t * 30)))
    if p is None: return
    o = min(1 if INTRO else kk(t, 0, .25), 1 - kk(t, END0 - .35, END0))
    if PES.get("escala", 1) != 1: p = p.resize((int(p.width * PES["escala"]), int(p.height * PES["escala"])), Image.LANCZOS)
    if PES.get("lado") == "dir": p = fade_base(p)
    if o < 1: p.putalpha(p.getchannel("A").point(lambda v: int(v * o)))
    x, y, _, _ = rect_small(p.width, p.height); im.alpha_composite(p, (int(x), int(y)))
if __name__ == "__main__":
    if len(sys.argv) > 1:
        for t in [float(x) for x in sys.argv[1:]]: frame(t).save("f_%05.1f.jpg" % t, quality=90)
    else:
        os.makedirs("saida", exist_ok=True); out = "saida/%s.mp4" % R.get("nome", "reel"); N = int(round(TOTAL * 30))
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", "30", "-i", "-", "-i", "audio.wav", "-t", "%.3f" % TOTAL, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        for i in range(N): p.stdin.write(np.asarray(frame(i / 30)).tobytes())
        p.stdin.close(); p.wait(); print("ok", out)
