"""Patch scoring.json (entrée encodeur+LM), puis mesure le rejeu. Usage : python essai_scoring.py patch alpha beta gamma lambda | score fichier"""
import json, sys
P = r"C:\Users\Doanh\Desktop\Programme IA\clavierPers\futo-keyboard\java\assets\futo-swipe\scoring.json"
K = "encoder:honorable_sturgeon contextlm:hungry_jellyfish"
if sys.argv[1] == "patch":
    d = json.load(open(P)); e = d[K]
    for name, v in zip(["alpha", "beta", "gamma", "lambda"], sys.argv[2:6]):
        if v != "-": e[name] = float(v)
    json.dump(d, open(P, "w"), indent=4); print(K, {k: e[k] for k in ["alpha", "beta", "gamma", "lambda"]})
else:
    it = json.load(open(sys.argv[2], encoding="utf-8"))["items"]
    f = lambda xs, k: 100 * sum(1 <= x["rank"] <= k for x in xs) / len(xs)
    a, b = it[:400], it[400:]
    print(f"réglage(400) {f(a,1):.1f}/{f(a,4):.1f} · contrôle({len(b)}) {f(b,1):.1f}/{f(b,4):.1f} · total {f(it,1):.1f}/{f(it,4):.1f}")
