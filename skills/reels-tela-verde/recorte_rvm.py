# Recorta a pessoa de um vídeo comum (sem tela verde) com Robust Video Matting e grava pessoa.mov (RGBA, qtrle)
# já enquadrada para o canto: corta a faixa de cima (crop_top, fração da altura), redimensiona para largura LW
# e desenha contorno marfim + sombra suave ("silhueta bem desenhada").
# Uso: python recorte_rvm.py entrada.mov pessoa.mov [largura=360] [crop_top=.2]
import sys, os, json, subprocess, numpy as np, cv2, torch
src, out = sys.argv[1], sys.argv[2]; LW = int(sys.argv[3]) if len(sys.argv) > 3 else 360; CT = float(sys.argv[4]) if len(sys.argv) > 4 else .2
torch.set_num_threads(2)
j = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", src]))["streams"][0]
w0, h0 = j["width"], j["height"]; w, h = w0, h0   # resolução cheia: borda mais limpa
MP = os.path.expanduser("~/.cache/rvm_mobilenetv3.torchscript")
if not os.path.exists(MP):
    import urllib.request; os.makedirs(os.path.dirname(MP), exist_ok=True)
    urllib.request.urlretrieve("https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.torchscript", MP)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
m = torch.jit.load(MP, map_location=DEV).eval(); rec = [None] * 4
y0 = int(h * CT); ch = h - y0; LH = int(round(LW * ch / w)) // 2 * 2; PAD = 14; OW, OH = LW + 2 * PAD, LH + PAD
rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", "scale=%d:%d" % (w, h), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
wr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", "%dx%d" % (OW, OH), "-r", "30", "-i", "-", "-c:v", "qtrle", out], stdin=subprocess.PIPE)
RING = np.array([248, 246, 242], np.float32); n = 0; PREV = [None]
while True:
    b = rd.stdout.read(w * h * 3)
    if len(b) < w * h * 3: break
    fr = np.frombuffer(b, np.uint8).reshape(h, w, 3)
    with torch.no_grad():
        t = torch.from_numpy(fr.copy()).permute(2, 0, 1)[None].float().to(DEV) / 255
        fgr, pha, *rec = m(t, *rec, .25)
    a = pha[0, 0].cpu().numpy(); f = fgr[0].permute(1, 2, 0).cpu().numpy() * 255
    a = a[y0:]; f = f[y0:]
    # estabiliza a máscara: só a maior região (a pessoa), sem buracos, e média com o quadro anterior (sem tremer a borda)
    hb = (a > .5).astype(np.uint8); nlab, lab, st, _ = cv2.connectedComponentsWithStats(hb, 8)
    if nlab > 1:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); keep = cv2.dilate((lab == big).astype(np.uint8), np.ones((15, 15), np.uint8)); a = a * keep
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    a = a if PREV[0] is None else .55 * a + .45 * PREV[0]; PREV[0] = a
    a = np.clip((a - .08) / .84, 0, 1); a = cv2.GaussianBlur(a, (0, 0), 1.2)
    a = cv2.resize(a, (LW, LH), interpolation=cv2.INTER_AREA); f = cv2.resize(f, (LW, LH), interpolation=cv2.INTER_AREA)
    A = np.zeros((OH, OW), np.float32); F = np.zeros((OH, OW, 3), np.float32); A[PAD:, PAD:PAD + LW] = a; F[PAD:, PAD:PAD + LW] = f
    hard = (A > .5).astype(np.uint8)
    ring = cv2.GaussianBlur(cv2.dilate(hard, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))).astype(np.float32), (0, 0), 1.0)
    sh = cv2.GaussianBlur(cv2.dilate(hard, np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 7) * .55
    col = np.zeros((OH, OW, 3), np.float32); al = sh.copy()                       # sombra preta
    col = col * (1 - ring[..., None]) + RING * ring[..., None]; al = np.maximum(al, ring)   # contorno
    col = col * (1 - A[..., None]) + F * A[..., None]; al = np.maximum(al, A)          # pessoa
    wr.stdin.write(np.dstack([col.clip(0, 255), al[..., None] * 255]).astype(np.uint8).tobytes()); n += 1
wr.stdin.close(); wr.wait(); json.dump(dict(w=OW, h=OH, quadros=n), open(os.path.splitext(out)[0] + ".json", "w")); print("ok", n, OW, OH)
