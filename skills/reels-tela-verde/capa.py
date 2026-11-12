# Capa do Reel (1080x1920, padrão do Instagram). Tudo o que importa fica dentro da área central 1080x1350
# (y 285 a 1635), que é o recorte 4:5 mostrado na grade do perfil.
# Uso (na pasta de trabalho, depois do render): python NF/capa.py capa.json
# capa.json: {"t": 3.0, "linha1": "STJ aumenta penas", "linha2": "do caso Boate Kiss", "pessoa_t": 12.4,
#             "lado": "dir", "saida": "saida/capa.png"}
#   t = instante da página (grifo do título visível, sem cartão); pessoa_t = quadro dele com boa expressão (boca fechada, olhar na câmera).
import sys, json, os
from PIL import Image, ImageDraw, ImageFilter
import nafonte as N, ui
cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "capa.json"))
W, H = 1080, 1920; t = cfg.get("t", 3.0)
base = N.frame_main(t)
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ui.draw_header(ov, t); base.alpha_composite(ov)
d = ImageDraw.Draw(base, "RGBA"); y0, y1 = 1030, 1290
d.rectangle([0, y0, W, y1], fill=(16, 38, 63, 238)); d.rectangle([0, y0, W, y0 + 5], fill=(201, 162, 75, 255)); d.rectangle([0, y1 - 5, W, y1], fill=(201, 162, 75, 255))
def fit(txt, mk, wmax, s0):
    s = s0
    while s > 40 and d.textlength(txt, font=mk(s)) > wmax: s -= 2
    return mk(s)
lado = cfg.get("lado", "dir"); xl = 60; wmax = W - 120
f1 = fit(cfg["linha1"], lambda s: ui.font(s, 900), wmax, 84); f2 = fit(cfg["linha2"], lambda s: ui.geo(s, italic=True, bold=True), wmax, 84)
d.text((xl, y0 + 98), cfg["linha1"], font=f1, fill=(248, 246, 242, 255), anchor="ls")
d.text((xl, y0 + 188), cfg["linha2"], font=f2, fill=(242, 201, 76, 255), anchor="ls")
ui.stext(d, xl, y1 - 20, "@OHERMENEUTA_ · NA FONTE", ui.font(24, 800), (217, 184, 101, 255), 3)
if cfg.get("sem_pessoa"):
    av = Image.open(os.path.join(os.path.dirname(os.path.abspath(N.__file__)), "assets", "avatar-hermeneuta.png")).convert("RGBA").resize((170, 170), Image.LANCZOS)
    mk = Image.new("L", (170, 170), 0); ImageDraw.Draw(mk).ellipse([0, 0, 169, 169], fill=255); av.putalpha(mk)
    d.ellipse([W // 2 - 91, 1371, W // 2 + 91, 1553], outline=(201, 162, 75, 255), width=5); base.alpha_composite(av, (W // 2 - 85, 1377))
    f = ui.font(34, 800); tx = "Siga @ohermeneuta_"; d.text(((W - d.textlength(tx, font=f)) / 2, 1610), tx, font=f, fill=(248, 246, 242, 255), anchor="ls")
elif N.PES:
    p = Image.open(cfg["pessoa_png"]).convert("RGBA") if cfg.get("pessoa_png") else N.pessoa_frame(int(round(cfg.get("pessoa_t", 5.0) * 30)))
    if p is not None:
        sc = cfg.get("escala", 1.18); p = p.resize((int(p.width * sc), int(p.height * sc)), Image.LANCZOS)
        x = W - p.width + 6 if lado == "dir" else -6; base.alpha_composite(p, (x, H - p.height))
os.makedirs(os.path.dirname(cfg.get("saida", "saida/capa.png")) or ".", exist_ok=True)
base.convert("RGB").save(cfg.get("saida", "saida/capa.png")); print("ok", cfg.get("saida", "saida/capa.png"))
