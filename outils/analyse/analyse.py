import json, sys
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
sw = [r for r in rows if r["kind"] == "swipe"]
und = {r["id"] for r in rows if r["kind"] == "undo"}
print("lignes", len(rows), "swipes", len(sw), "annules", len(und))
for r in sw[:60]:
    w = [c["word"].lower() for c in r["results"]]
    t = r["target"].lower()
    pts = len(r["left"][0]["x"]) if r["left"] else 0
    dur = r["left"][0]["t"][-1] if r["left"] else 0
    print("X" if r["id"] in und else " ", t.ljust(12), "rang", (w.index(t) + 1) if t in w else 0,
          "pts", pts, "ms", int(dur), "beam", r["beam"], "->", w[:4])
if sw:
    print("layout", sw[0]["letters"], "n_ids_uniques", len({r["id"] for r in sw}))
    print("taille moyenne ligne", sum(len(json.dumps(r)) for r in sw) // len(sw))
