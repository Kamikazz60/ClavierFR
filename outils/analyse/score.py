import json, sys, unicodedata, collections
def na(s): return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
und = {r["id"] for r in rows if r["kind"] == "undo"}
sw = [r for r in rows if r["kind"] == "swipe"]
valid = [r for r in sw if r["id"] not in und]
def rank(r, f=lambda s: s):
    w = [f(c["word"].lower()) for c in r["results"]]
    t = f(r["target"].lower())
    return w.index(t) + 1 if t in w else 0
def stats(rs, label):
    n = len(rs)
    if not n: return
    t1 = sum(rank(r) == 1 for r in rs); t4 = sum(1 <= rank(r) <= 4 for r in rs)
    a1 = sum(rank(r, na) == 1 for r in rs); a4 = sum(1 <= rank(r, na) <= 4 for r in rs)
    print(f"{label:28s} n={n:4d}  top1 {100*t1/n:5.1f}%  top4 {100*t4/n:5.1f}%   (sans accents {100*a1/n:5.1f}% / {100*a4/n:5.1f}%)")
print("swipes bruts", len(sw), "annules", len(und), "valides", len(valid))
stats(valid, "TOUS (valides)")
stats(sw, "TOUS (y compris refaits)")
stats([r for r in valid if len(r["target"]) <= 2], "mots 1-2 lettres")
stats([r for r in valid if 3 <= len(r["target"]) <= 4], "mots 3-4 lettres")
stats([r for r in valid if 5 <= len(r["target"]) <= 7], "mots 5-7 lettres")
stats([r for r in valid if len(r["target"]) >= 8], "mots 8+ lettres")
stats([r for r in valid if "'" in r["target"]], "avec apostrophe")
stats([r for r in valid if na(r["target"]) != r["target"].lower()], "avec accent")
# erreurs les plus frequentes (cibles ratees au top-1)
miss = collections.Counter(r["target"].lower() for r in valid if rank(r) != 1)
print("rates top-1 (distincts):", len(miss), "|", ", ".join(f"{w}x{c}" if c > 1 else w for w, c in miss.most_common(40)))
# mots refaits : le tracé annulé etait-il pire ?
byw = collections.defaultdict(list)
for r in sw: byw[(r["sentence"], r["wordIndex"])].append(r)
redo = [v for v in byw.values() if len(v) > 1]
print("mots refaits:", len(redo), "| 1er essai top1:", sum(rank(v[0]) == 1 for v in redo), "-> dernier essai top1:", sum(rank(v[-1]) == 1 for v in redo))
print("phrases couvertes:", len({r["sentence"] for r in valid}), "| mots distincts:", len({r["target"].lower() for r in valid}))
# parasites dans les propositions (mots non francais frequents)
bad = collections.Counter(c["word"].lower() for r in valid for c in r["results"][:1] if c["word"].lower() != r["target"].lower())
print("top-1 erronés les plus frequents:", bad.most_common(15))

# --- mesure sans biais : premier essai de chaque mot ---
first = [v[0] for v in sorted(byw.values(), key=lambda v: v[0]["id"])]
print()
stats(first, "PREMIER ESSAI (sans biais)")
stats([r for r in first if len(r["target"]) <= 2], " 1-2 lettres")
stats([r for r in first if 3 <= len(r["target"]) <= 4], " 3-4 lettres")
stats([r for r in first if 5 <= len(r["target"]) <= 7], " 5-7 lettres")
stats([r for r in first if len(r["target"]) >= 8], " 8+ lettres")
stats([r for r in first if "'" in r["target"]], " apostrophe")
stats([r for r in first if na(r["target"]) != r["target"].lower()], " accent")
