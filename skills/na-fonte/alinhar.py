# Alinha as palavras da legenda (roteiro.frases[].tela) ao áudio final com o Whisper; o que não casar é interpolado entre vizinhas.
import json
import words
def nz(s): return s.strip(" .,:;?!").lower()
def alinhar(wav="audio.wav"):
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8"); import subprocess as _sp, soundfile as _sf; _sp.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", "16000", "_16k.wav"], check=True); A, _ = _sf.read("_16k.wav", dtype="float32")
    best = None
    for prompt in (None, " ".join(f["tela"] for f in words.R["frases"])[:220]):
        segs, _ = m.transcribe(A, language="pt", word_timestamps=True, beam_size=5, initial_prompt=prompt)
        W = [(nz(w.word), w.start, w.end) for s in segs for w in s.words]; out = _casar(W)
        sc = sum(o[4] for o in out)
        if best is None or sc > best[0]: best = (sc, out)
        if sc >= .7 * len(out): break
    out = best[1]; n = len(out); i = 0
    return _fim(out)
def _casar(W):
    out = []; j = 0
    for tok, a, b, si in words.build():
        hit = next((k for k in range(j, min(j + 5, len(W))) if W[k][0] == nz(tok)), None)
        if hit is not None: out.append([tok, W[hit][1], W[hit][2], si, 1]); j = hit + 1
        else: out.append([tok, a, b, si, 0])
    return out
def _fim(out):
    n = len(out); i = 0
    while i < n:
        if out[i][4] == 0:
            j = i
            while j < n and out[j][4] == 0: j += 1
            a = out[i - 1][2] if i > 0 else out[i][1]; b = out[j][1] if j < n else out[j - 1][2]
            ws = [len(w[0].strip(".,;:?")) + 1 + (3 if w[0][-1] in ".?" else 0) for w in out[i:j]]; tot = sum(ws); c = a
            for k, w in zip(range(i, j), ws): d = (b - a) * w / tot; out[k][1] = round(c, 3); out[k][2] = round(c + d * .9, 3); c += d
            i = j
        else: i += 1
    json.dump(out, open("align.json", "w"), ensure_ascii=False); return sum(o[4] for o in out), n
if __name__ == "__main__": print(alinhar())
