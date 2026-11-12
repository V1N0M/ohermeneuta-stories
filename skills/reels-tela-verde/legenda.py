# Confere a legenda do post do Reel: <= 2.200 caracteres, no máximo 2 emojis (padrão: só 📌), 3 a 5 hashtags,
# sem exclamação, com a fonte citada e a chamada para @ohermeneuta_. Uso: python NF/legenda.py saida/<nome>-legenda.txt
import sys, re
s = open(sys.argv[1], encoding="utf-8").read(); prob = []
emo = re.findall(r"[\U0001F300-\U0001FAFF☀-➿⭐✅]", s); tags = re.findall(r"#\w+", s)
if len(s) > 2200: prob.append("passou de 2.200 caracteres (%d)" % len(s))
if len(emo) > 2: prob.append("emojis demais (%d): %s" % (len(emo), " ".join(emo)))
if not 3 <= len(tags) <= 5: prob.append("use 3 a 5 hashtags (tem %d)" % len(tags))
if "!" in s: prob.append("tem exclamação: tom sóbrio, sem '!'")
if "@ohermeneuta_" not in s: prob.append("falta a chamada para seguir @ohermeneuta_")
if not re.search(r"(?i)fonte", s): prob.append("falta a linha de fonte")
if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", s): prob.append("data com barras: use 10-11-2026")
print("%d caracteres | %d emojis | %d hashtags" % (len(s), len(emo), len(tags))); print("OK" if not prob else "AJUSTAR:\n- " + "\n- ".join(prob))
