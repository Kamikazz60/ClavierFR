"""Exporte le ContextLM entraîné en .pte (ExecuTorch + XNNPACK) au format attendu par swipe-library.

Produit dans --out : context_lm.pte, metadata.json, vocab.txt, et affiche la liste des opérateurs
non délégués pour la comparer à celle de l'.aar embarqué (swipe-library/models/*/ops.txt).
"""
import argparse, json, os, shutil
import torch
from model import ContextLM, Exportable

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True)          # dossier avec model.pt
ap.add_argument("--data", required=True)         # dossier avec vocab.txt / meta.json
ap.add_argument("--out", required=True)
ap.add_argument("--codename", default="french_lm")
ap.add_argument("--hash_penalty", type=float, default=0.0)  # retranché au score de chaque mot haché
ap.add_argument("--allowed", default="")         # fichier(s) ops.txt autorisés, séparés par des virgules
args = ap.parse_args()

res = json.load(open(os.path.join(args.run, "result.json")))["args"]
meta = json.load(open(os.path.join(args.data, "meta.json")))
lm = ContextLM(meta["num_exact"], meta["buckets"], res["dim"], res["hidden"], res["layers"], ctx=res["ctx"])
lm.load_state_dict(torch.load(os.path.join(args.run, "model.pt")))
lm.eval()
with torch.no_grad(): lm.hash_bias -= args.hash_penalty / 2   # un mot haché = somme de 2 buckets
L = res["ctx"]


class Emb(torch.nn.Module):
    def __init__(self, lm):
        super().__init__(); self.lm = lm

    def forward(self):
        a, b, c, d = self.lm.embeddings()
        return a, b, c, d


from executorch.exir import to_edge_transform_and_lower
from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner

ids = torch.zeros(1, L, dtype=torch.int64)
hashes = torch.zeros(1, L, 2, dtype=torch.int64)
programs = {
    "forward": torch.export.export(Exportable(lm), (ids, hashes)),
    "get_embeddings": torch.export.export(Emb(lm), ()),
}
edge = to_edge_transform_and_lower(programs, partitioner={"forward": [XnnpackPartitioner()], "get_embeddings": []})
prog = edge.to_executorch()

os.makedirs(args.out, exist_ok=True)
with open(os.path.join(args.out, "context_lm.pte"), "wb") as f:
    f.write(prog.buffer)
json.dump({"kind": "contextlm", "codename": args.codename}, open(os.path.join(args.out, "metadata.json"), "w"), indent=2)
shutil.copy(os.path.join(args.data, "vocab.txt"), os.path.join(args.out, "vocab.txt"))
print("écrit :", os.path.join(args.out, "context_lm.pte"), f"{os.path.getsize(os.path.join(args.out, 'context_lm.pte'))/1e6:.1f} Mo")

# opérateurs utilisés (hors délégué) pour chaque méthode
used = set()
for plan in prog.executorch_program.execution_plan:
    names = [op.name + ("." + op.overload if op.overload else "") for op in plan.operators]
    print(f"méthode {plan.name} : {len(names)} opérateurs :", sorted(names))
    used.update(names)
if args.allowed:
    allowed = set()
    for p in args.allowed.split(","):
        allowed.update(l.strip() for l in open(p) if l.strip())
    extra = sorted(n for n in used if n not in allowed and n.split("::")[0] != "executorch_prim")
    print("opérateurs HORS liste autorisée :", extra if extra else "aucun")
