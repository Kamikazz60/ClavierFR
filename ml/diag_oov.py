import json, numpy as np, torch, random, string
from model import ContextLM
from common import hash_indices
d="data/fw"; meta=json.load(open(f"{d}/meta.json")); res=json.load(open("runs/fw1/result.json"))["args"]
lm=ContextLM(meta["num_exact"],meta["buckets"],res["dim"],res["hidden"],res["layers"],ctx=res["ctx"]); lm.load_state_dict(torch.load("runs/fw1/model.pt")); lm.eval()
val=np.load(f"{d}/tokens_val.npy"); L=16; N=meta["num_exact"]
vocab=["<OOV>"]+open(f"{d}/vocab.txt",encoding="utf-8").read().split("\n")
win=np.stack([val[s:s+L] for s in range(1000,1000+16*200,16)]).astype(np.int64)
ids=torch.from_numpy(np.where(win>=N,N,win)); hs=torch.zeros(ids.shape+(2,),dtype=torch.long)
with torch.no_grad():
    h=lm(ids,hs)[:,-1]
    ex=h@lm.exact_embed.weight.T+lm.exact_bias
    ex[:,0]=-1e9
    lse=torch.logsumexp(ex,1)
    random.seed(0)
    fake=["".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(3,8))) for _ in range(300)]
    hi=torch.tensor([hash_indices(w,meta["buckets"]) for w in fake],dtype=torch.long)
    he=lm.hash_embed(hi).sum(1); hb=lm.hash_bias[hi].sum(1)
    hl=h@he.T+hb
print("exact : logit moyen des mots vocab", float(ex.mean()), "| max moyen", float(ex.max(1).values.mean()), "| lse moyen", float(lse.mean()))
print("hash  : logit moyen de mots inventés", float(hl.mean()), "| max moyen", float(hl.max(1).values.mean()))
print("part des mots inventés dont le score dépasse le meilleur mot réel :", float((hl>ex.max(1).values[:,None]).float().mean()))
