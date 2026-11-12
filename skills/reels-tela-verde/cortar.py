# Decupagem e corte do vídeo bruto do apresentador (formato "Na fonte").
#   python cortar.py transcrever bruto.mp4 [--modelo small|medium]
#       -> bruto_tr.json (palavras com tempos) e lista das frases com tempos na tela. Você escolhe as tomadas boas.
#   python cortar.py montar bruto.mp4 trechos.json [--vel 1.04] [--xf 0.15] [--cauda 2.5]
#       trechos.json = [[ini, fim], ...] em segundos do bruto, UM trecho por frase do roteiro (mesma ordem de roteiro.json "frases").
#       Refina cada borda pela energia do áudio (respiro ~0,12 s antes, ~0,18 s depois), corta trecho a trecho,
#       une com transição suave (dissolve de imagem + crossfade de áudio de --xf s) e acelera tudo levemente (--vel).
#       -> cut.mov (1080x1920, 30 fps), audio.wav (-14 LUFS, com a cauda do cartão final), tempos.json (frases, END0, TOTAL, CLICK)
import sys, json, subprocess, argparse, os
import numpy as np
def sh(c): subprocess.run(c, check=True)
def wav(src, dst, sr):
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(sr), dst])
def ler(p):
    import soundfile as sf; a, sr = sf.read(p, dtype="float32"); return a, sr
def transcrever(src, modelo):
    from faster_whisper import WhisperModel
    import subprocess as _sp, soundfile as _sf; _sp.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", "_16k.wav"], check=True); a, _ = _sf.read("_16k.wav", dtype="float32"); m = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(a, language="pt", word_timestamps=True, beam_size=5); out = []
    for s in segs:
        print("%6.2f %6.2f %s" % (s.start, s.end, s.text)); out += [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for w in s.words]
    json.dump(out, open(os.path.splitext(os.path.basename(src))[0] + "_tr.json", "w"), ensure_ascii=False)
def refinar(trechos, a, sr):
    hop = int(.01 * sr); db = 20 * np.log10(np.array([np.sqrt(np.mean(a[i:i + hop] ** 2) + 1e-12) for i in range(0, len(a) - hop, hop)]))
    thr = np.percentile(db, 8) + 15; out = []
    for s, e in trechos:
        i0, i1 = max(0, int((s - .5) * 100)), int((s + .3) * 100); on = next((i for i in range(i0, i1) if db[i] > thr), int(s * 100)) / 100
        j0, j1 = min(len(db) - 1, int((e + .6) * 100)), int((e - .3) * 100); off = next((i for i in range(j0, j1, -1) if db[i] > thr), int(e * 100)) / 100
        out.append([round(max(0, on - .12), 3), round(off + .18, 3)])
    for k in range(1, len(out)):          # nunca sobrepor trechos vizinhos do bruto
        if out[k][0] < out[k - 1][1]: m = (out[k][0] + out[k - 1][1]) / 2; out[k - 1][1] = m; out[k][0] = m
    return out
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
def montar(src, trechos, vel, xf, cauda):
    wav(src, "_b48.wav", 48000); a, sr = ler("_b48.wav"); S = refinar(trechos, a, sr); print("trechos refinados:", S)
    for i, (s, e) in enumerate(S):    # trecho a trecho (vários trims do mesmo arquivo estouram a memória)
        sh(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-i", src, "-t", "%.3f" % (e - s), "-vf", "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", "_s%d.mov" % i])
    D = [dur("_s%d.mov" % i) for i in range(len(S))]; ins = []; fc = []; vl, al = "0:v", "0:a"; L = D[0]
    for i in range(len(S)): ins += ["-i", "_s%d.mov" % i]
    for i in range(1, len(S)):
        fc.append("[%s][%d:v]xfade=transition=fade:duration=%s:offset=%.3f[vx%d];[%s][%d:a]acrossfade=d=%s:c1=tri:c2=tri[ax%d]" % (vl, i, xf, L - xf, i, al, i, xf, i))
        vl, al = "vx%d" % i, "ax%d" % i; L += D[i] - xf
    fc.append("[%s]setpts=PTS/%s[vo];[%s]atempo=%s[ao]" % (vl, vel, al, vel))
    sh(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[vo]", "-map", "[ao]", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-c:a", "pcm_s16le", "cut.mov"])
    t = 0; seg = []
    for d in D: seg.append((t / vel, (t + d) / vel)); t += d - xf
    Lv = L / vel; sent = [[round(x + .11, 3), round(y - .16, 3)] for x, y in seg]; END0 = round(Lv + .3, 3); TOTAL = round(END0 + cauda, 3)
    json.dump(dict(sent=sent, seg_ini=[s[0] for s in sent], END0=END0, TOTAL=TOTAL, CLICK=round(END0 + 1.25, 3), fator=vel, aviso=None), open("tempos.json", "w"))
    wav("cut.mov", "_voz.wav", 48000); v, _ = ler("_voz.wav"); n = int(TOTAL * sr); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    e = int(Lv * sr); f = int(.08 * sr); v[max(0, e - f):e] *= np.linspace(1, 0, len(v[max(0, e - f):e])); v[e:] = 0
    import soundfile as sf; sf.write("_voz_pad.wav", v, sr)
    sh(["ffmpeg", "-v", "error", "-y", "-i", "_voz_pad.wav", "-af", "highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000", "audio.wav"])
    for i in range(len(S)): os.remove("_s%d.mov" % i)
    print("ok: cut.mov %.2f s | vídeo final %.2f s (com cartão final)" % (Lv, TOTAL)); print("frases:", sent)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("acao"); ap.add_argument("bruto"); ap.add_argument("trechos", nargs="?")
    ap.add_argument("--modelo", default="small"); ap.add_argument("--vel", type=float, default=1.04); ap.add_argument("--xf", type=float, default=.15); ap.add_argument("--cauda", type=float, default=2.5)
    a = ap.parse_args()
    if a.acao == "transcrever": transcrever(a.bruto, a.modelo)
    else: montar(a.bruto, json.load(open(a.trechos)), a.vel, a.xf, a.cauda)
