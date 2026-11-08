import json, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
b=json.load(open("replay_fr_lm2.json",encoding="utf-8")); it=b["items"]
voc=set(open("../ml/data/fw/vocab.txt",encoding="utf-8").read().split("\n"))
lost=[x for x in it if x["rankOrig"]==1 and x["rank"]!=1]; won=[x for x in it if x["rankOrig"]!=1 and x["rank"]==1]
print("perdus (1->autre):",len(lost),"gagnés:",len(won),"| déjà ok:",sum(x["rankOrig"]==1 and x["rank"]==1 for x in it))
w=collections.Counter(x["top4"][0] for x in lost); print("vainqueurs à tort les plus fréquents :",w.most_common(12))
inv=sum(x["top4"][0].lower() in voc for x in lost); print("vainqueur à tort dans le vocabulaire LM :",inv,"/",len(lost))
tv=sum(x["target"].lower() in voc for x in lost); print("cible dans le vocabulaire LM :",tv,"/",len(lost))
for x in lost[:14]: print(x["target"],"->",x["top4"])
allw=[x["top4"][0] for x in it]; print("mots top-1 hors vocab (tous):",sum(a.lower() not in voc for a in allw),"/",len(allw))
