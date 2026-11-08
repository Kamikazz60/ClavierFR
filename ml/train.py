"""Entraînement du ContextLM français sur CPU (softmax échantillonné, évaluation en softmax complet)."""
import argparse, json, math, os, time
import numpy as np
import torch
import torch.nn.functional as F
from model import ContextLM

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--minutes", type=float, default=10)
ap.add_argument("--max_steps", type=int, default=0)
ap.add_argument("--batch", type=int, default=256)
ap.add_argument("--ctx", type=int, default=16)
ap.add_argument("--dim", type=int, default=64)
ap.add_argument("--hidden", type=int, default=256)
ap.add_argument("--layers", type=int, default=4)
ap.add_argument("--neg", type=int, default=4096)
ap.add_argument("--lr", type=float, default=3e-3)
ap.add_argument("--eval_every", type=int, default=500)
ap.add_argument("--resume", default="")
ap.add_argument("--threads", type=int, default=4)
args = ap.parse_args()
torch.set_num_threads(args.threads)
torch.manual_seed(0); np.random.seed(0)
os.makedirs(args.out, exist_ok=True)

meta = json.load(open(os.path.join(args.data, "meta.json")))
N, B = meta["num_exact"], meta["buckets"]
train = np.load(os.path.join(args.data, "tokens_train.npy"))
val = np.load(os.path.join(args.data, "tokens_val.npy"))
oov_hash = np.load(os.path.join(args.data, "oov_hash.npy"))
oov_hash_t = torch.from_numpy(oov_hash.astype(np.int64)) if len(oov_hash) else torch.zeros(1, 2, dtype=torch.int64)
L = args.ctx
zeros_idx = np.flatnonzero(train == 0)
print(f"train {len(train):,} tokens · val {len(val):,} · {len(zeros_idx):,} débuts de paragraphe · "
      f"OOV {meta['oov_rate_train']*100:.1f} %", flush=True)

# distribution de tirage des négatifs : fréquence^0.75 sur les mots exacts
cnt = np.bincount(train[train < N], minlength=N).astype(np.float64)
cnt[0] = 0
q = cnt ** 0.75; q /= q.sum()
log_q = torch.from_numpy(np.log(np.maximum(q, 1e-12)).astype(np.float32))
q_t = torch.from_numpy(q.astype(np.float32))

model = ContextLM(N, B, args.dim, args.hidden, args.layers, ctx=L)
if args.resume:
    model.load_state_dict(torch.load(args.resume))
print("paramètres :", sum(p.numel() for p in model.parameters()), flush=True)
opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01, betas=(0.9, 0.98))


def to_inputs(win):
    """win: int array [b, L+1] -> (ids, hashes, targets) en tenseurs."""
    w = torch.from_numpy(win.astype(np.int64))
    inp, tgt = w[:, :L], w[:, 1:]
    is_oov = inp >= N
    hashes = torch.zeros(inp.shape + (2,), dtype=torch.int64)
    if is_oov.any():
        hashes[is_oov] = oov_hash_t[inp[is_oov] - N]
    ids = torch.where(is_oov, torch.full_like(inp, N), inp)
    return ids, hashes, tgt


def sample_windows(data, b):
    starts = np.random.randint(0, len(data) - L - 1, size=b)
    # une partie des fenêtres démarre à un début de paragraphe, avec ou sans le marqueur 0
    k = int(b * 0.2)
    if k and len(zeros_idx):
        z = zeros_idx[np.random.randint(0, len(zeros_idx), size=k)]
        z = np.minimum(z + (np.random.rand(k) < 0.5), len(data) - L - 2)
        starts[:k] = z
    return np.stack([data[s:s + L + 1] for s in starts])


def oov_logits(model, h, tgt):
    """Score des cibles hors vocabulaire : h . (e1+e2) + (b1+b2)."""
    m = tgt >= N
    if not m.any():
        return m, None
    hs = oov_hash_t[tgt[m] - N]
    e = model.hash_embed(hs).sum(1)
    return m, (h[m] * e).sum(-1) + model.hash_bias[hs].sum(1)


def loss_sampled(model, ids, hashes, tgt):
    h = model(ids, hashes).reshape(-1, args.dim)
    t = tgt.reshape(-1)
    valid = t != 0                                    # on ne prédit pas le marqueur de début
    h, t = h[valid], t[valid]
    is_oov, s_oov = oov_logits(model, h, t)
    neg = torch.multinomial(q_t, args.neg, replacement=False)
    W, bias = model.exact_embed.weight, model.exact_bias
    t_ex = t.clamp(max=N - 1)
    true_logit = (h * W[t_ex]).sum(-1) + bias[t_ex]
    if s_oov is not None:
        true_logit = true_logit.clone(); true_logit[is_oov] = s_oov
    true_logit = true_logit - torch.where(is_oov, torch.zeros_like(true_logit), log_q[t_ex] + math.log(args.neg))
    neg_logit = h @ W[neg].T + bias[neg] - (log_q[neg] + math.log(args.neg))
    hit = (t_ex.unsqueeze(1) == neg.unsqueeze(0)) & ~is_oov.unsqueeze(1)
    neg_logit = neg_logit.masked_fill(hit, -1e9)
    lse = torch.logsumexp(torch.cat([true_logit.unsqueeze(1), neg_logit], 1), 1)
    return (lse - true_logit).mean()


@torch.no_grad()
def evaluate(model, tokens=60000):
    model.eval()
    n = min(tokens, len(val) - L - 2)
    starts = np.arange(0, n, L)
    tot = cnt_t = top1 = top4 = 0
    W, bias = model.exact_embed.weight, model.exact_bias
    for i in range(0, len(starts), 128):
        win = np.stack([val[s:s + L + 1] for s in starts[i:i + 128]])
        ids, hashes, tgt = to_inputs(win)
        h = model(ids, hashes).reshape(-1, args.dim)
        t = tgt.reshape(-1)
        v = t != 0
        h, t = h[v], t[v]
        logits = h @ W.T + bias
        logits[:, 0] = -1e9
        is_oov, s_oov = oov_logits(model, h, t)
        lse = torch.logsumexp(logits, 1)
        true = logits.gather(1, t.clamp(max=N - 1).unsqueeze(1)).squeeze(1)
        if s_oov is not None:
            true = true.clone(); true[is_oov] = s_oov
            lse = torch.where(is_oov, torch.logaddexp(lse, torch.zeros_like(lse) + true), lse)
        tot += float((lse - true).sum()); cnt_t += len(t)
        top = logits.topk(4, 1).indices
        ex = ~is_oov
        top1 += int((top[ex][:, 0] == t[ex]).sum()); top4 += int((top[ex] == t[ex].unsqueeze(1)).any(1).sum())
    model.train()
    return math.exp(tot / cnt_t), top1 / cnt_t, top4 / cnt_t


t0 = time.time(); step = 0; ema = None
while True:
    elapsed = (time.time() - t0) / 60
    if elapsed >= args.minutes or (args.max_steps and step >= args.max_steps):
        break
    frac = elapsed / args.minutes if not args.max_steps else step / args.max_steps
    lr = args.lr * min(1.0, (step + 1) / 200) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * frac)))
    for g in opt.param_groups: g["lr"] = lr
    ids, hashes, tgt = to_inputs(sample_windows(train, args.batch))
    loss = loss_sampled(model, ids, hashes, tgt)
    opt.zero_grad(set_to_none=True); loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step(); step += 1
    ema = loss.item() if ema is None else 0.98 * ema + 0.02 * loss.item()
    if step % 100 == 0:
        print(f"étape {step} · {elapsed:.1f} min · {step*args.batch*L/(time.time()-t0):,.0f} tok/s · perte {ema:.3f} · lr {lr:.5f}", flush=True)
    if step % args.eval_every == 0:
        ppl, a1, a4 = evaluate(model, 30000)
        print(f"  >> validation : perplexité {ppl:.1f} · top-1 {a1*100:.1f} % · top-4 {a4*100:.1f} %", flush=True)
        torch.save(model.state_dict(), os.path.join(args.out, "model.pt"))

torch.save(model.state_dict(), os.path.join(args.out, "model.pt"))
ppl, a1, a4 = evaluate(model, 200000)
print(f"FINAL · {step} étapes · validation : perplexité {ppl:.1f} · top-1 {a1*100:.1f} % · top-4 {a4*100:.1f} %", flush=True)
json.dump(dict(steps=step, ppl=ppl, top1=a1, top4=a4, args=vars(args)), open(os.path.join(args.out, "result.json"), "w"), indent=1)
