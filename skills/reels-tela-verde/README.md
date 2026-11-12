# Reels tela verde ("Na fonte") — Reel d'O Hermeneuta sobre a página oficial da notícia

Formato aprovado em 12-11-2026 (caso Boate Kiss, nota do STJ de 10-11-2026).
No centro, a câmera percorre o print real da notícia/julgado e grifa em dourado o trecho que está sendo falado.
O apresentador aparece recortado do fundo (efeito de tela verde, sem precisar de tela verde) no canto esquerdo
ou direito, com contorno claro. A voz é a do vídeo bruto, cortada sem saltos e levemente acelerada.

## Instalação (uma vez)

Requisitos: Python 3.10+, Node 18+, ffmpeg no PATH. Funciona em Linux, macOS e Windows (PowerShell).

```
git clone --depth 1 https://github.com/V1N0M/ohermeneuta-stories
cd ohermeneuta-stories/skills/reels-tela-verde
pip install -r requirements.txt          # no Linux da nuvem: pip install --break-system-packages -r requirements.txt
npm install && npx playwright install chromium
```
O modelo de recorte (RVM, ~15 MB) baixa sozinho na primeira vez para `~/.cache`.
O Whisper (`small`) também baixa sozinho na primeira vez.

## Comandos, na ordem (rode dentro da pasta de trabalho do vídeo)

`NF` = caminho desta pasta (`skills/reels-tela-verde`). A pasta de trabalho é qualquer outra (ex.: `reel-kiss/`).

1. **Transcrever o bruto** e escolher as tomadas:
   `python NF/cortar.py transcrever bruto.mp4` → `bruto_tr.json` + frases com tempos na tela.
   Fique com a ÚLTIMA tomada completa de cada frase; descarte repetições e frases interrompidas.
2. **roteiro.json**: uma entrada em `frases` por trecho, com `tela` = exatamente o que foi falado (grafia correta,
   números em algarismos, nomes certos). Modelo: `exemplos/boate-kiss/roteiro.json`
   (`nome`, `selo`, `capitulos` [[rótulo, índice da frase]], `rotulo_fixo: ""`, `lancamento`, `fontes`).
3. **trechos.json**: `[[ini, fim], ...]` em segundos do bruto, um por frase, na mesma ordem.
4. **Cortar e acelerar**: `python NF/cortar.py montar bruto.mp4 trechos.json --vel 1.04`
   → `cut.mov`, `audio.wav` (-14 LUFS), `tempos.json`. Bordas refinadas pela energia do áudio,
   dissolve de 0,15 s entre cortes, velocidade 1,03–1,06 (padrão 1,04). Meta: vídeo final ≤ 40 s.
5. **Capturar a página oficial**: `cfg.json` com `titleRe` (regex do título), `vw: 520` (layout de celular, texto grande),
   `names: []` e `passages` {id: trecho EXATO copiado da página}. Depois:
   `node NF/capturar_pagina.mjs "<url>" cfg.json` → `page.png`, `rects.json`, `page_text.txt` (lista `missing` deve vir vazia;
   se faltar, copie o trecho de `page_text.txt`, que é o texto normalizado da página).
6. **Alinhar a legenda à fala**: `python NF/alinhar.py` → `align.json` (imprime casadas/total; acima de ~80% está bom).
   Consulte os índices das palavras por frase: `python -c "import sys; sys.path.insert(0,'NF'); import words; [print(i,k,w) for k,(w,a,b,i) in enumerate(words.WORDS)]"`.
7. **Recortar o apresentador**: `python NF/recorte_rvm.py cut.mov pessoa.mov 360 0.18`
   (largura 360 px no vídeo final; 0.18 = fração do topo do quadro descartada, acima da cabeça). Gera `pessoa.json`.
8. **nafonte.json** (modelo em `exemplos/boate-kiss/nafonte.json`): varreduras (grifos), chips de fonte, cartões e `pessoa`.
9. **Testar quadros**: `python NF/nafonte.py 1 7 12 19 25 33` → `f_XX.X.jpg`. Olhe cada um: grifo no trecho certo,
   nada cortado, cartão dentro da caixa (máx. 2 linhas a 35–37 px), pessoa sem resto de fundo.
10. **Render**: `python NF/nafonte.py` → `saida/<nome>.mp4` (1080x1920, 30 fps, H.264 + AAC).
11. **Conferir**: `ffprobe` (duração ≤ 40 s), prancha de 16 quadros, ouvir no celular.
12. **Capa** (1080x1920; o essencial fica no centro 1080x1350, que é o recorte da grade do perfil):
    `capa.json` {t, linha1, linha2, pessoa_t, lado, saida} → `python NF/capa.py capa.json`.
    Opções: `pessoa_png` (recorte pronto de um quadro escolhido, ex.: antes de começar a falar, sorrindo de boca fechada)
    ou `sem_pessoa: true` (avatar + "Siga @ohermeneuta_"). Procure o quadro no BRUTO inteiro, não só no vídeo cortado.
    `linha1` curta em branco (o fato), `linha2` em itálico dourado (o caso). Escolha `pessoa_t` num quadro com boca
    fechada e olhar na câmera (gere 3–4 opções e compare). Sem exclamação, até ~28 caracteres por linha.
13. **Legenda do post** (`saida/<nome>-legenda.txt`): tom sóbrio e jornalístico, 1 frase de abertura com o fato,
    1 parágrafo por ponto (decisão com 📌 + processo + órgão + data; contexto; fundamento), linha "Fonte: ...",
    chamada "Siga @ohermeneuta_" e 5 hashtags. Máx. 2.200 caracteres; 📌 é o único emoji (no máximo 2);
    sem exclamação e sem pergunta retórica; datas 10-11-2026. Confira: `python NF/legenda.py saida/<nome>-legenda.txt`.

## Elementos padrão que sempre saem no vídeo (não remover)
- **Legenda karaokê** (palavra falada em destaque dourado) = texto de `roteiro.json` alinhado à fala.
- **Barra de progresso segmentada** no topo + faixa "DIREITO FORA DOS AUTOS · @OHERMENEUTA_".
- **Nome/selo do caso** (`roteiro.selo`, ex.: "CASO BOATE KISS · STJ") e etiqueta de capítulo (`roteiro.capitulos`).
- **Cartão final** (2,5 s): marca, lançamento do site (`roteiro.lancamento`; depois de 17-11-2026 vira "o site já está no ar")
  e o botão "Seguir" clicado, que vira "Seguindo".

## nafonte.json

```json
{"pagina": "page.png",
 "sweeps": [ {"id": "titulo", "rect": "titulo", "sent": 0, "from": 4, "to": 14},
             {"id": "nome1", "rect": "nome1", "sent": 1, "from": 0, "to": 11, "zoom": 0.8} ],
 "chips":  [ {"sent": 0, "texto": "NOTA OFICIAL DO STJ · 10-11-2026"}, {"sent": 6, "texto": "FONTE: STJ · REsp 2.256.938"} ],
 "cards":  [ {"tipo": "nota", "sent": 2, "from": 11, "label": "SEGUNDO A NOTA DO STJ", "texto": "...", "fs": 37} ],
 "pessoa": {"arquivo": "pessoa.mov", "lado": "esq", "x": 4}}
```
- `sweeps`: `rect` = id de `passages`; `sent` = índice da frase; `from`/`to` = índices das palavras (na frase) em que o grifo
  começa e termina; `at` + `dur` para um grifo curto. Siga a ORDEM DA PÁGINA: a câmera só desce (nunca volta para cima).
- `zoom` (opcional, ~0,8): aproxima e acompanha a linha de um lado para o outro, devagar. Use em 2–3 trechos curtos e
  importantes (nomes, números, a frase central). Sem `zoom`, a coluna inteira cabe na tela e a câmera só rola.
- Frase sem grifo (ex.: comentário do apresentador) → câmera parada + um cartão.
- `pessoa.lado`: `esq` ou `dir`. Fica no canto inferior, abaixo da legenda; some suavemente no cartão final.
- Ajustes finos: `move_thr` (.22), `glide_max` (1.8 s), `cam_sigma` (.18 s), `dim` (.5, escurece fora do trecho).

## Entregas
`saida/<nome>.mp4`, `saida/capa.png`, `saida/<nome>-legenda.txt`, prancha `saida/qc.jpg` e a lista de fontes no chat.

## As 8 ferramentas do editor (use só as que a notícia pedir; no máximo 2 cartões extras por vídeo)

| # | Ferramenta | Gatilho na notícia | Como usar |
|---|---|---|---|
| 1 | **Grifo sincronizado** (sempre) | todo trecho citado na fala | `sweeps` |
| 2 | **Lupa / câmera na fonte** | nome, número, frase decisiva | `sweeps[].zoom` ~0,8 |
| 3 | **Nota de margem** ("em linguagem simples" / "segundo a nota") | termo técnico, fundamento, motivo | card `nota` |
| 4 | **Escada de números (redline)** | pena, valor, prazo ou índice que mudou | card `escada` (cols com `tok_r`, valor antigo riscado quando o novo aparece) |
| 5 | **Linha do tempo** | sequência de fases datadas (fato → 1ª inst. → tribunal → STJ/STF) | card `linha` `itens:[{data,texto,tok}]` |
| 6 | **Glossário oficial** | termo difícil com definição do próprio tribunal (ex.: glossário da notícia do STJ) | card `glossario` com `credito` |
| 7 | **Quadro de votos** | relator vencido, divergência, placar | card `votos` `linhas:[{nome,voto,vencedor,tok}]` |
| 8 | **Dossiê de fontes** | o caso depende de mais de um documento oficial (nota + acórdão + nota do MP) | card `dossie` `docs:[{img,rotulo,tok}]` (cada `img` é outra captura feita com `capturar_pagina.mjs`) |

Extra: **carimbo "NÃO INFORMADO"** (`carimbos`) só quando a fala aponta algo que a fonte não diz.
Se a notícia não tem o gatilho, a ferramenta não entra.

Cada cartão: `sent` (frase), `from`/`to` (palavras de entrada/saída), `off`/`offb` (ajuste em s), `label`, `texto`, `fs`.
Todo texto de cartão vem da fonte (nunca inventar); números e datas conferidos.

## Abertura opcional
`abertura_pasta.py` (foto de pasta + carimbo + capa abrindo) existe, mas o formato aprovado vai direto para a notícia.
