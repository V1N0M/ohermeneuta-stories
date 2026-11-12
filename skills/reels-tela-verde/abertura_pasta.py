# Abertura "pasta do caso": foto da pasta, carimbo vermelho cai sobre o título, a capa da pasta abre em 3D
# (perspectiva, dobradiça à esquerda) e revela a folha da notícia; a câmera aproxima e entrega para o "Na fonte".
# cfg (nafonte.json -> "abertura"): foto, capa [[x,y]...] (px da foto, sem a aba do fundo), titulo [x0,y0,x1,y1],
#   carimbo ["O CASO","BOATE KISS"], t_carimbo, t_abre, dur_abre, t_fim, folha [x0,y0,x1,y1] (px da foto), folha_css [y0,y1]
import math, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
W, H = 1080, 1920
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def eout(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
class Pasta:
    def __init__(s, cfg, page, dsf, font):
        s.c = cfg; ph = Image.open(cfg["foto"]).convert("RGB"); pw, phh = ph.size; s.k = k = W / pw; s.oy = int(round((H - phh * k) / 2))
        P = np.asarray(ph.resize((W, int(round(phh * k))), Image.LANCZOS)).astype(np.float32); s.PH_ = P.shape[0]
        bw = int(round(pw * H / phh)); bg = np.asarray(ph.resize((bw, H), Image.LANCZOS)).astype(np.float32)[:, (bw - W) // 2:(bw - W) // 2 + W]
        s.BG = cv2.GaussianBlur(bg, (0, 0), 28) * .55
        sc = lambda pts: [(x * k, y * k) for x, y in pts]
        poly = sc(cfg["capa"]); m = Image.new("L", (W, s.PH_), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
        s.MASK = np.asarray(m.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]; s.bx0, s.bx1, s.by0, s.by1 = int(min(xs)), int(math.ceil(max(xs))), int(min(ys)), int(math.ceil(max(ys)))
        # capa sem texto (miolo da pasta / verso da capa)
        u8 = P.astype(np.uint8); hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV); gray = cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY)
        red = (P[..., 0] - P[..., 1] > 55) & (P[..., 0] < 200); txt = ((gray < 110) | red) & (s.MASK > .5)
        txt = cv2.dilate(txt.astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
        blank = cv2.inpaint(u8, txt, 9, cv2.INPAINT_TELEA).astype(np.float32); blank = cv2.GaussianBlur(blank, (0, 0), 1.0)
        s.BLANK = blank
        # miolo: capa removida, fundo da pasta um pouco mais escuro; folha da notícia por cima
        ins = P * (1 - s.MASK[..., None]) + blank * .88 * s.MASK[..., None]
        fx0, fy0, fx1, fy1 = [v * k for v in cfg["folha"]]; fw, fh = int(fx1 - fx0), int(fy1 - fy0)
        y0c, y1c = cfg["folha_css"]; crop = page[int(y0c * dsf):int(y1c * dsf)]; crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        cw = crop.shape[1]; ch = int(cw * fh / fw); crop = crop[:ch]; sheet = cv2.resize(crop, (fw - 36, fh - 36), interpolation=cv2.INTER_AREA).astype(np.float32)
        paper = np.full((fh, fw, 3), 250, np.float32); paper[18:18 + sheet.shape[0], 18:18 + sheet.shape[1]] = sheet
        paper *= (.93 + .07 * np.linspace(0, 1, fh, dtype=np.float32))[:, None, None]
        rot = cfg.get("folha_rot", -1.2); Mr = cv2.getRotationMatrix2D((fw / 2, fh / 2), rot, 1.0)
        pr = cv2.warpAffine(paper, Mr, (fw, fh), borderValue=(0, 0, 0)); am = cv2.warpAffine(np.ones((fh, fw), np.float32), Mr, (fw, fh))
        sh = np.zeros(ins.shape[:2], np.float32); X0, Y0 = int(fx0), int(fy0); sh[Y0 + 14:Y0 + 14 + fh, X0 + 10:X0 + 10 + fw] = am; sh = cv2.GaussianBlur(sh, (0, 0), 14)
        ins *= (1 - .38 * sh)[..., None]; reg = ins[Y0:Y0 + fh, X0:X0 + fw]; ins[Y0:Y0 + fh, X0:X0 + fw] = reg * (1 - am[..., None]) + pr * am[..., None]
        s.INS = ins; s.SHEET_C = ((fx0 + fx1) / 2, fy0 + fh * cfg.get("folha_foco", .28))
        s.P = P; s.font = font; s.stamp = s._stamp(); s.cover_tex = None
    def _stamp(s):
        x0, y0, x1, y1 = [v * s.k for v in s.c["titulo"]]; pad = 26; w, h = int(x1 - x0 + pad * 2), int((y1 - y0) * 1.3 + pad * 2)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); red = (176, 22, 26)
        d.rounded_rectangle([0, 0, w - 1, h - 1], 14, fill=red + (240,)); d.rounded_rectangle([12, 12, w - 13, h - 13], 9, outline=(238, 214, 170, 255), width=5)
        l1, l2 = s.c.get("carimbo", ["O CASO", "BOATE KISS"])
        for size in range(150, 40, -4):
            f2 = s.font(size, 900)
            if d.textlength(l2, font=f2) + 9 * len(l2) < w - 90: break
        f1 = s.font(int(size * .5), 900)
        def ctext(y, t, f, ls):
            tw = d.textlength(t, font=f) + ls * (len(t) - 1); x = (w - tw) / 2
            for c in t: d.text((x, y), c, font=f, fill=(0, 0, 0, 0), anchor="ls"); x += d.textlength(c, font=f) + ls
        shape = Image.new("L", (w, h), 0); ImageDraw.Draw(shape).rounded_rectangle([0, 0, w - 1, h - 1], 14, fill=255)
        ctext(h * .42, l1, f1, 10); ctext(h * .86, l2, f2, 9)
        a = np.asarray(im).astype(np.float32); g = np.random.default_rng(7)
        nz = cv2.GaussianBlur(g.random((h, w)).astype(np.float32), (0, 0), 2.2); nz = (nz - nz.min()) / (nz.max() - nz.min())
        a[..., 3] *= np.clip(.78 + nz * .5, 0, 1) * (g.random((h, w)) > .012)
        rot = s.c.get("carimbo_rot", 4); out = Image.fromarray(a.astype(np.uint8)).rotate(rot, expand=True, resample=Image.BICUBIC)
        s.shape = np.asarray(shape.rotate(rot, expand=True, resample=Image.BICUBIC), np.float32) / 255
        s.st_c = ((x0 + x1) / 2, (y0 + y1) / 2 - (y1 - y0) * .05); return out
    def _with_stamp(s, base, t):
        tc = s.c["t_carimbo"]; ta = tc - .28
        if t < ta: return base, 0.0
        u = min(1, (t - ta) / .28); sc = 1 + 1.5 * (1 - eout(u)); al = min(1, u * 2.5)
        st = s.stamp; w, h = int(st.width * sc), int(st.height * sc); im = np.asarray(st.resize((w, h), Image.BICUBIC)).astype(np.float32)
        out = base.copy(); cx, cy = s.st_c; x, y = int(cx - w / 2), int(cy - h / 2)
        if u < 1:   # sombra do carimbo no ar
            sh = cv2.GaussianBlur(im[..., 3], (0, 0), 10 + 30 * (1 - u)) / 255 * .45 * al; dx = int(40 * (1 - u)); s._blend(out, np.zeros_like(im[..., :3]), sh, x + dx, y + dx)
        if u >= 1: s._blend(out, s.BLANK[max(0, y):, :][:0] if False else s._crop(s.BLANK, x, y, w, h), s.shape, x, y)
        else: s._blend(out, np.full((h, w, 3), (236, 214, 172), np.float32), cv2.resize(s.shape, (w, h)) * al, x, y)
        alpha = im[..., 3] / 255 * al; s._blend(out, im[..., :3] * (.82 + .18 * s._paper(x, y, w, h, base)), alpha, x, y)
        shake = math.exp(-(t - tc) * 18) * math.sin((t - tc) * 70) * 9 if t >= tc else 0
        return out, shake
    def _crop(s, img, x, y, w, h):
        out = np.zeros((h, w, 3), np.float32); X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(W, x + w), min(img.shape[0], y + h)
        out[Y0 - y:Y1 - y, X0 - x:X1 - x] = img[Y0:Y1, X0:X1]; return out
    def _paper(s, x, y, w, h, base):   # textura do papel sob a tinta
        X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(W, x + w), min(base.shape[0], y + h); g = np.ones((h, w, 1), np.float32)
        if X1 > X0 and Y1 > Y0: g[Y0 - y:Y1 - y, X0 - x:X1 - x, 0] = base[Y0:Y1, X0:X1].mean(-1) / 200
        return np.clip(g, .6, 1.15)
    def _blend(s, dst, src, a, x, y):
        h, w = a.shape; X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
        if X1 <= X0 or Y1 <= Y0: return
        aa = a[Y0 - y:Y1 - y, X0 - x:X1 - x, None]; dst[Y0:Y1, X0:X1] = dst[Y0:Y1, X0:X1] * (1 - aa) + src[Y0 - y:Y1 - y, X0 - x:X1 - x] * aa
    def _flip(s, t, closed):
        ta, dur = s.c["t_abre"], s.c.get("dur_abre", 1.1); th = math.pi * ease((t - ta) / dur)
        if s.cover_tex is None:
            bx0, bx1, by0, by1 = s.bx0, s.bx1, s.by0, s.by1
            s.cover_tex = (closed[by0:by1, bx0:bx1].copy(), s.MASK[by0:by1, bx0:bx1].copy(), s.BLANK[by0:by1, bx0:bx1][:, ::-1].copy() * 1.04, s.MASK[by0:by1, bx0:bx1][:, ::-1].copy())
        ft, fm, bt, bm = s.cover_tex; out = s.INS.copy(); w, h = s.bx1 - s.bx0, s.by1 - s.by0
        f = 2300.0; yc = (s.by0 + s.by1) / 2; sz = f / (f - w * math.sin(th)); xe = s.bx0 + w * math.cos(th) * sz
        far = [(xe, yc + (s.by0 - yc) * sz), (xe, yc + (s.by1 - yc) * sz)]; hin = [(s.bx0, s.by0), (s.bx0, s.by1)]
        if th < math.pi / 2: tex, msk = ft, fm; dst = [hin[0], far[0], far[1], hin[1]]; shade = .5 + .5 * math.cos(th)
        else: tex, msk = bt, bm; dst = [far[0], hin[0], hin[1], far[1]]; shade = .62 + .38 * abs(math.cos(th))
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]]); M = cv2.getPerspectiveTransform(src, np.float32(dst))
        wt = cv2.warpPerspective(tex, M, (W, out.shape[0]), flags=cv2.INTER_LINEAR); wm = cv2.warpPerspective(msk, M, (W, out.shape[0]))
        # sombra projetada pela capa levantada
        sm = cv2.GaussianBlur(np.roll(np.roll(wm, int(28 * math.sin(th)), 1), int(36 * math.sin(th)), 0), (0, 0), 6 + 26 * math.sin(th))
        out *= (1 - .5 * math.sin(th) * sm)[..., None]
        out = out * (1 - wm[..., None]) + wt * shade * wm[..., None]; return out
    def frame(s, t):
        """devolve RGB float32 HxW do quadro da abertura"""
        closed, shake = s._with_stamp(s.P, t)
        img = closed if t < s.c["t_abre"] else s._flip(t, closed)
        can = s.BG.copy(); y0 = s.oy; fe = 70
        a = np.ones(img.shape[0], np.float32); a[:fe] = np.linspace(0, 1, fe); a[-fe:] = np.linspace(1, 0, fe)
        can[y0:y0 + img.shape[0]] = can[y0:y0 + img.shape[0]] * (1 - a[:, None, None]) + img * a[:, None, None]
        # câmera: leve aproximação; depois do abrir, mergulha na folha
        tz0 = s.c["t_abre"] + s.c.get("dur_abre", 1.1) - .15; tz1 = s.c["t_fim"]
        z0 = 1 + .035 * min(1, t / max(.1, tz0)); u = ease((t - tz0) / max(.1, tz1 - tz0)); z = z0 * (1 + (s.c.get("zoom_folha", 1.75) - 1) * u)
        ax, ay = s.c.get("alvo", [W / 2, H / 2]); sx = W / 2 + (ax - W / 2) * u; sy = H / 2 + (ay - H / 2) * u
        cx0, cy0 = W / 2, H / 2; cx1, cy1 = s.SHEET_C[0], s.SHEET_C[1] + y0; cx = cx0 + (cx1 - cx0) * u; cy = cy0 + (cy1 - cy0) * u
        M = np.float32([[z, 0, sx - cx * z], [0, z, sy - cy * z + shake]])
        return cv2.warpAffine(can, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
