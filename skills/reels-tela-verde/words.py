# Palavras da legenda com tempos. Lê roteiro.json (frases[].tela) e tempos.json; se existir align.json (Whisper), usa os tempos medidos.
import json, os
R = json.load(open("roteiro.json")); TM = json.load(open("tempos.json")); SENT = TM["sent"]
DISP = [f["tela"] for f in R["frases"]]
def _peso(w):
    b = w.strip(".,;:?!")
    if any(c.isdigit() for c in b): return 6 + 4 * len(b)
    return len(b)
def build():
    out = []
    for i, s in enumerate(DISP):
        a, b = SENT[i]; toks = s.split(); ws = []
        for w in toks:
            n = _peso(w) + 1
            if w[-1] in ".?!": n += 4
            elif w[-1] in ",;:": n += 2.5
            ws.append(n)
        tot = sum(ws); c = a
        for w, n in zip(toks, ws):
            d = (b - a) * n / tot; out.append((w, c, c + d * (1 - (0.35 if w[-1] in ".?!,;:" else 0)), i)); c += d
    return out
WORDS = build()
if os.path.exists("align.json"):
    _al = json.load(open("align.json"))
    if [a[0] for a in _al] == [w[0] for w in WORDS]: WORDS = [(a[0], a[1], max(a[2], a[1] + .08), a[3]) for a in _al]
def T(token, occ=0):
    k = 0
    for w, a, b, i in WORDS:
        if w.strip(".,;:?!").lower() == token.lower():
            if k == occ: return a
            k += 1
    raise KeyError("palavra não encontrada na legenda: %s (ocorrência %d)" % (token, occ))
