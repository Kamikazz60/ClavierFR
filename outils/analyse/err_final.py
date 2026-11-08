import json, sys, unicodedata, collections
sys.stdout.reconfigure(encoding="utf-8")
na=lambda s:"".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn").lower()
it=json.load(open("replay_final.json",encoding="utf-8"))["items"]
n=len(it); ok=[x for x in it if x["rank"]==1]; bad=[x for x in it if x["rank"]!=1]
print("top1",len(ok),"/",n)
cat=collections.Counter()
for x in bad:
    t=x["target"].lower(); w=[c.lower() for c in x["top4"]]
    if x["rank"]==0: k="absent du top-4 (accent seul)" if any(na(c)==na(t) for c in w) else "absent du top-4"
    else: k="dans le top-4 (rang %d)"%x["rank"]
    if x["rank"]==0 and not any(na(c)==na(t) for c in w): k="absent du top-4"
    cat[k]+=1
for k,v in cat.most_common(): print(v,k)
print("--- exemples rang 0:")
for x in [b for b in bad if b["rank"]==0][:25]: print(x["target"],"->",x["top4"])
L=lambda f:sum(1 for x in it if f(x["target"]))
print("cibles courtes (<=3 lettres) ratées:",sum(len(x["target"])<=3 for x in bad),"/",sum(len(x["target"])<=3 for x in it))
print("cibles avec apostrophe/trait d'union ratées:",sum(("'" in x["target"] or "’" in x["target"] or "-" in x["target"]) for x in bad),"/",sum(("'" in x["target"] or "’" in x["target"] or "-" in x["target"]) for x in it))
