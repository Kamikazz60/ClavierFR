"""Recalibre les tables hachées (mots hors vocabulaire) : softmax échantillonné avec négatifs, reste du modèle figé."""
import argparse, json, math, os, time, numpy as np, torch
from model import ContextLM
from common import hash_indices
ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--run", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--minutes", type=float, default=20); ap.add_argument("--batch", type=int, default=256)
ap.add_argument("--neg", type=int, default=1024); ap.add_argument("--lr", type=float, default=3e-3); ap.add_argument("--threads", type=int, default=4)
a = ap.parse_args(); torch.set_num_threads(a.threads); torch.manual_seed(1); np.random.seed(1)
meta = json.load(open(f"{a.data}/meta.json")); res = json.load(open(f"{a.run}/result.json"))["args"]
N, B, L = meta["num_exact"], meta["buckets"], res["ctx"]
lm = ContextLM(N, B, res["dim"], res["hidden"], res["layers"], ctx=L); lm.load_state_dict(torch.load(f"{a.run}/model.pt")); lm.eval()
for p in lm.parameters(): p.requires_grad = False
lm.hash_embed.weight.requires_grad = True; lm.hash_bias.requires_grad = True
vocab = open(f"{a.data}/vocab.txt", encoding="utf-8").read().split("\n")[:N - 1]
VH = torch.zeros(N, 2, dtype=torch.long)
for i, w in enumerate(vocab): VH[i + 1] = torch.tensor(hash_indices(w, B))
train = np.load(f"{a.data}/tokens_train.npy"); val = np.load(f"{a.data}/tokens_val.npy")
oovh = torch.from_numpy(np.load(f"{a.data}/oov_hash.npy").astype(np.int64))
cnt = np.bincount(train[train < N], minlength=N).astype(np.float64); cnt[0] = 0
q = cnt ** 0.75; q /= q.sum(); q_t = torch.from_numpy(q.astype(np.float32)); log_q = torch.from_numpy(np.log(np.maximum(q, 1e-12)).astype(np.float32))
opt = torch.optim.AdamW([lm.hash_embed.weight, lm.hash_bias], lr=a.lr, weight_decay=0.0)

def inputs(win):
    w = torch.from_numpy(win.astype(np.int64)); inp, tgt = w[:, :L], w[:, 1:]
    oo = inp >= N; hs = torch.zeros(inp.shape + (2,), dtype=torch.long)
    if oo.any(): hs[oo] = oovh[inp[oo] - N]
    return torch.where(oo, torch.full_like(inp, N), inp), hs, tgt

def hscore(h, hi):  # h [n,E], hi [n,2] -> [n]
    return (h * lm.hash_embed(hi).sum(1)).sum(-1) + lm.hash_bias[hi].sum(1)

def step_loss(data, b):
    s = np.random.randint(0, len(data) - L - 1, size=b)
    ids, hs, tgt = inputs(np.stack([data[i:i + L + 1] for i in s]))
    with torch.no_grad(): h = lm(ids, hs).reshape(-1, res["dim"])
    t = tgt.reshape(-1); v = t != 0; h, t = h[v], t[v]
    oo = t >= N; t_ex = t.clamp(max=N - 1)
    hi_t = torch.where(oo.unsqueeze(1), oovh[(t - N).clamp(min=0)] if len(oovh) else VH[t_ex], VH[t_ex])
    tl = hscore(h, hi_t) - torch.where(oo, torch.zeros_like(h[:, 0]), log_q[t_ex] + math.log(a.neg))
    neg = torch.multinomial(q_t, a.neg, replacement=False)
    he = lm.hash_embed(VH[neg]).sum(1); hb = lm.hash_bias[VH[neg]].sum(1)
    nl = h @ he.T + hb - (log_q[neg] + math.log(a.neg))
    nl = nl.masked_fill((t_ex.unsqueeze(1) == neg.unsqueeze(0)) & ~oo.unsqueeze(1), -1e9)
    soft = (torch.logsumexp(torch.cat([tl.unsqueeze(1), nl], 1), 1) - tl).mean()
    # ancrage : le score haché doit imiter le score exact (niveau absolu comparable), mots tirés uniformément
    u = torch.randint(1, N, (1024,)); hu = lm.hash_embed(VH[u]).sum(1); hbu = lm.hash_bias[VH[u]].sum(1)
    with torch.no_grad(): eu = h @ lm.exact_embed.weight[u].T + lm.exact_bias[u]
    anchor = ((h @ hu.T + hbu - eu) ** 2).mean()
    return soft * 0.2 + anchor * 0.05

@torch.no_grad()
def check():
    s = np.arange(1000, 1000 + L * 200, L)
    ids, hs, _ = inputs(np.stack([val[i:i + L + 1] for i in s])); h = lm(ids, hs)[:, -1]
    ex = h @ lm.exact_embed.weight.T + lm.exact_bias; ex[:, 0] = -1e9
    he = lm.hash_embed(VH[1:2000]).sum(1); hl = h @ he.T + lm.hash_bias[VH[1:2000]].sum(1)
    import random, string; random.seed(0)
    fk = torch.tensor([hash_indices("".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(3, 8))), B) for _ in range(300)])
    fl = h @ lm.hash_embed(fk).sum(1).T + lm.hash_bias[fk].sum(1)
    print(f"  contrôle : meilleur mot réel {float(ex.max(1).values.mean()):.1f} | mots inventés moyen {float(fl.mean()):.1f}, max {float(fl.max(1).values.mean()):.1f}, "
          f"dépassent le meilleur réel {float((fl > ex.max(1).values[:, None]).float().mean())*100:.1f} % | mots vocab via hachage (moy.) {float(hl.mean()):.1f}", flush=True)

check(); t0 = time.time(); k = 0; ema = None
while (time.time() - t0) / 60 < a.minutes:
    fr = (time.time() - t0) / 60 / a.minutes
    for g in opt.param_groups: g["lr"] = a.lr * min(1, (k + 1) / 100) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * fr)))
    loss = step_loss(train, a.batch); opt.zero_grad(); loss.backward(); opt.step(); k += 1
    ema = loss.item() if ema is None else 0.98 * ema + 0.02 * loss.item()
    if k % 100 == 0: print(f"étape {k} · {(time.time()-t0)/60:.1f} min · perte {ema:.3f}", flush=True)
    if k % 500 == 0: check()
os.makedirs(a.out, exist_ok=True)
import shutil; shutil.copy(f"{a.run}/result.json", f"{a.out}/result.json"); torch.save(lm.state_dict(), f"{a.out}/model.pt")
check(); print("FINI", flush=True)
