import json, sys, numpy as np, torch
from model import ContextLM
sys.stdout.reconfigure(encoding="utf-8")
d = "data/mini"; meta = json.load(open(f"{d}/meta.json")); res = json.load(open("runs/mini/result.json"))["args"]
lm = ContextLM(meta["num_exact"], meta["buckets"], res["dim"], res["hidden"], res["layers"], ctx=res["ctx"]); lm.load_state_dict(torch.load("runs/mini/model.pt")); lm.eval()
L = res["ctx"]
ids = torch.randint(1, 1000, (1, L)); h = torch.zeros(1, L, 2, dtype=torch.long)
a = lm(ids, h)
ids2 = ids.clone(); ids2[0, 10:] = torch.randint(1, 1000, (L - 10,))
b = lm(ids2, h)
print("fuite causale ? écart max sur positions < 10 :", float((a[0, :10] - b[0, :10]).abs().max()), "| positions >= 10 :", float((a[0, 10:] - b[0, 10:]).abs().max()))
vocab = ["<OOV>"] + open(f"{d}/vocab.txt", encoding="utf-8").read().split("\n")
val = np.load(f"{d}/tokens_val.npy"); train = np.load(f"{d}/tokens_train.npy")
dec = lambda t: "·" if t == 0 else (vocab[t] if t < len(vocab) else "<hash>")
print("échantillon val :", " ".join(dec(t) for t in val[2000:2060]))
# doublons entre train et val (fenêtres de 8 mots)
def grams(x, n=8): return {tuple(x[i:i+n]) for i in range(0, len(x) - n, 4)}
gv, gt = grams(val[:60000]), grams(train)
print("fenêtres de 8 mots du val présentes dans le train :", len(gv & gt), "/", len(gv))
