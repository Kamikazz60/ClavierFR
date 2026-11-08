"""Prépare le corpus du ContextLM : comptage des mots, vocabulaire, encodage en identifiants.

Conventions (imposées par swipe-library/src/context_lm.cpp) :
  - id 0 = <OOV>, aussi utilisé comme « début de paragraphe » (contexte vide = que des 0) ;
  - ids 1..V = mots du vocabulaire (ligne i de vocab.txt -> id i) ;
  - mot hors vocabulaire = id NUM_EXACT (= V+1), avec ses 2 buckets hachés (wyhash).
Sortie dans --out : vocab.txt, tokens.npy (int32, ids ; >= NUM_EXACT => index de la table OOV),
oov_hash.npy (int32 [n,2]), meta.json.
"""
import argparse, array, collections, json, os, time
import numpy as np
import pyarrow.parquet as pq
from common import tokenize, hash_indices

ap = argparse.ArgumentParser()
ap.add_argument("--parquet", nargs="+", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--num_exact", type=int, default=32768)      # taille de la table exacte (id 0 inclus)
ap.add_argument("--buckets", type=int, default=32768)        # buckets hachés (puissance de 2)
ap.add_argument("--max_docs", type=int, default=0)           # 0 = tout
ap.add_argument("--min_tokens", type=int, default=4)         # paragraphes plus courts ignorés
ap.add_argument("--val_docs", type=int, default=2000)        # documents réservés à la validation
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
V = args.num_exact - 1


def paragraphs(files):
    n = 0
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(batch_size=512, columns=["text"]):
            for text in batch.column("text").to_pylist():
                if not text:
                    continue
                yield n, [t for t in (tokenize(p) for p in text.split("\n")) if len(t) >= args.min_tokens]
                n += 1
                if args.max_docs and n >= args.max_docs:
                    return


t0 = time.time()
print("passe 1 : comptage des mots…", flush=True)
counts = collections.Counter()
ndocs = 0
for n, paras in paragraphs(args.parquet):
    ndocs = n + 1
    for p in paras:
        counts.update(p)
    if len(counts) > 20_000_000:                      # élagage mémoire : on oublie les mots vus une seule fois
        counts = collections.Counter({w: c for w, c in counts.items() if c > 1})
    if n % 20000 == 0 and n:
        print(f"  {n} documents, {len(counts)} mots distincts, {time.time()-t0:.0f}s", flush=True)
total_words = sum(counts.values())
print(f"  {ndocs} documents, {total_words} mots, {len(counts)} distincts")

vocab = [w for w, _ in counts.most_common(V)]
NL = chr(10)
with open(os.path.join(args.out, "vocab.txt"), "w", encoding="utf-8", newline=NL) as f:
    f.write(NL.join(vocab) + NL)
word2id = {w: i + 1 for i, w in enumerate(vocab)}
covered = sum(counts[w] for w in vocab) / total_words
print(f"vocabulaire : {len(vocab)} mots, couvre {covered*100:.2f} % des mots du corpus", flush=True)
del counts

print("passe 2 : encodage…", flush=True)
NUM_EXACT = args.num_exact
oov_index = {}
oov_hash = []


def encode(word):
    i = word2id.get(word)
    if i is not None:
        return i
    j = oov_index.get(word)
    if j is None:
        j = len(oov_hash)
        oov_index[word] = j
        oov_hash.append(hash_indices(word, args.buckets))
    return NUM_EXACT + j


train = array.array("i")
val = array.array("i")
for n, paras in paragraphs(args.parquet):
    dest = val if n < args.val_docs else train
    for p in paras:
        dest.append(0)                                # début de paragraphe (= <OOV>/BOS)
        dest.extend(encode(w) for w in p)
    if n % 20000 == 0 and n:
        print(f"  {n} documents, {len(train):,} mots d'entraînement, {len(oov_hash):,} OOV distincts, {time.time()-t0:.0f}s", flush=True)

train = np.frombuffer(train, dtype=np.int32).copy()
val = np.frombuffer(val, dtype=np.int32).copy()
np.save(os.path.join(args.out, "tokens_train.npy"), train)
np.save(os.path.join(args.out, "tokens_val.npy"), val)
np.save(os.path.join(args.out, "oov_hash.npy"), np.asarray(oov_hash, dtype=np.int32).reshape(-1, 2))
meta = dict(num_exact=NUM_EXACT, buckets=args.buckets, vocab=len(vocab), train_tokens=int(len(train)),
            val_tokens=int(len(val)), oov_distinct=len(oov_hash), coverage=covered,
            oov_rate_train=float((train >= NUM_EXACT).mean()))
json.dump(meta, open(os.path.join(args.out, "meta.json"), "w"), indent=1)
print(meta)
print(f"temps total {time.time()-t0:.0f}s")
