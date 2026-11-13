# Efeitos sonoros do "Na fonte" (sintetizados, sem direitos autorais), mixados por baixo da voz.
# Uso (na pasta de trabalho, depois de nafonte.json pronto): python NF/sfx.py
#   lê audio.wav (voz) -> guarda em audio_voz.wav na 1ª vez -> grava audio.wav = voz + efeitos.
# Efeitos: carimbo (intro.t_carimbo), "whoosh" no encolher da abertura e em cada movimento de câmera (zoom/rolagem),
# "tic" quando entra um cartão, clique + "plim" no botão Seguir do cartão final.
import os, sys, json, shutil, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt
sys.argv = [sys.argv[0]]
import nafonte as N
if not os.path.exists("audio_voz.wav"): shutil.copy("audio.wav", "audio_voz.wav")
v, sr = sf.read("audio_voz.wav", dtype="float32")
if v.ndim > 1: v = v.mean(1)
fx = np.zeros_like(v); g = np.random.default_rng(3)
def bp(x, a, b): return sosfilt(butter(2, [a, min(b, sr * .45)], "band", fs=sr, output="sos"), x)
def put(x, t, gain):
    i = int(t * sr)
    if i < 0 or i >= len(fx): return
    m = min(len(x), len(fx) - i); fx[i:i + m] += x[:m] * gain
def carimbo():
    n = int(.6 * sr); t = np.arange(n) / sr
    boom = np.sin(2 * np.pi * np.cumsum(48 + 90 * np.exp(-t * 28)) / sr) * np.exp(-t * 9)
    slap = bp(g.standard_normal(n), 300, 4000) * np.exp(-t * 45); rub = bp(g.standard_normal(n), 120, 900) * np.exp(-t * 14) * .5
    return boom * .9 + slap * .8 + rub
def whoosh(d):
    n = int(d * sr); t = np.arange(n) / sr; u = t / d; env = np.sin(np.pi * u) ** 1.6; out = np.zeros(n); seg = 10
    nz = g.standard_normal(n)
    for s in range(seg):
        a, b = int(n * s / seg), int(n * (s + 1) / seg); fc = 500 + 2600 * np.sin(np.pi * (s + .5) / seg); out[a:b] = bp(nz[a:b], fc * .6, fc * 1.6)
    return out * env
def tic():
    n = int(.12 * sr); t = np.arange(n) / sr; return (np.sin(2 * np.pi * 1850 * t) * .6 + bp(g.standard_normal(n), 2000, 7000) * .4) * np.exp(-t * 55)
def clique():
    n = int(.08 * sr); t = np.arange(n) / sr; return bp(g.standard_normal(n), 1500, 8000) * np.exp(-t * 120) + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 90) * .5
def plim():
    n = int(1.2 * sr); t = np.arange(n) / sr; y = np.zeros(n)
    for f, a in ((1568, 1), (2093, .6), (3136, .25)): y += a * np.sin(2 * np.pi * f * t) * np.exp(-t * 4.5)
    return y * (1 - np.exp(-t * 300)) * .5
ev = []
I = N.CFG.get("intro")
if I:
    put(carimbo(), I.get("t_carimbo", .45) - .01, .55); ev.append(("carimbo", I.get("t_carimbo", .45)))
    put(whoosh(I.get("transicao", .7) + .2), I["fim"] - .1, .22); ev.append(("whoosh-intro", I["fim"]))
# movimentos de câmera: trechos em que a câmera anda/aproxima
T, X, Y, S = N.CT, N.CX, N.CY, N.CS
sp = np.abs(np.gradient(Y)) * 120 * S + np.abs(np.gradient(X)) * 120 * S + np.abs(np.gradient(np.log(S))) * 120 * 900
mov = sp > 140; i = 0
while i < len(mov):
    if mov[i]:
        j = i
        while j < len(mov) and mov[j]: j += 1
        d = (j - i) / 120
        if d > .35 and T[i] > .3 and T[i] < N.END0 - .3: put(whoosh(min(1.6, max(.5, d))), T[i] - .05, .16); ev.append(("whoosh", round(T[i], 2)))
        i = j
    else: i += 1
for c in N.CFG.get("cards", []):
    a = (N.tok(c["sent"], c["from"])[0] if c.get("from") is not None else N.SENT[c["sent"]][0]) + c.get("off", 0); put(tic(), a, .18); ev.append(("tic", round(a, 2)))
put(clique(), N.TM["CLICK"], .5); put(plim(), N.TM["CLICK"] + .1, .32); ev.append(("clique+plim", N.TM["CLICK"]))
mix = v + fx; mix /= max(1, np.abs(mix).max() / .97); sf.write("audio.wav", mix, sr); print("efeitos:", ev)
