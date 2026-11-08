import json, sys, unicodedata, collections
sys.stdout.reconfigure(encoding="utf-8")
def na(s): return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
sw = [r for r in rows if r["kind"] == "swipe"]
byw = collections.defaultdict(list)
for r in sw: byw[(r["sentence"], r["wordIndex"])].append(r)
first = [v[0] for v in sorted(byw.values(), key=lambda v: v[0]["id"])]
def words(r): return [c["word"].lower() for c in r["results"]]
def show(title, rs, n=22):
    print("\n==", title, len(rs))
    for r in rs[:n]:
        w = words(r); t = r["target"].lower()
        print(f'  {t:14s} rang {(w.index(t)+1) if t in w else 0}  -> {w[:4]}')
apos = [r for r in first if "'" in r["target"]]
show("APOSTROPHE (premier essai)", apos)
acc = [r for r in first if na(r["target"]) != r["target"].lower() and words(r)[:1] != [r["target"].lower()]]
show("ACCENT rates", acc, 30)
# la cible apparait-elle un jour dans les propositions (tous essais confondus) ?
ever = collections.defaultdict(bool)
for r in sw:
    ever[r["target"].lower()] |= r["target"].lower() in words(r)
never = sorted(t for t, ok in ever.items() if not ok)
print("\n== cibles jamais proposees, tous essais confondus:", len(never), "/", len(ever))
print("  ", ", ".join(never))
# type d'accent des ratés jamais proposés
print("\n== candidats parasites (hors dictionnaire francais probable) dans les top-4 :")
cnt = collections.Counter(w for r in first for w in words(r)[:4] if w != r["target"].lower())
print("  ", [w for w, c in cnt.most_common(60)])
