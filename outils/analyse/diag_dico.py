import gzip, re, sys, json, collections, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
path = sys.argv[1]
lines = gzip.open(path, "rt", encoding="utf-8").read().splitlines()
print("en-tete:", lines[0][:200])
words = {}
for l in lines[1:]:
    m = re.match(r"\s*word=([^,]*),f=(\d+)(.*)", l)
    if m:
        words[m.group(1)] = (int(m.group(2)), m.group(3))
print("mots:", len(words))
fr = [w for w in words if "'" in w]
print("avec apostrophe:", len(fr), "ex:", fr[:15])
# elisions par prefixe
pref = collections.Counter(w.split("'")[0] for w in fr)
print("prefixes d'elision:", pref.most_common(15))
# cibles ratees : presentes ou non ?
rows = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8")]
tg = sorted({r["target"].lower() for r in rows if r["kind"] == "swipe"})
missing = [t for t in tg if t not in words]
print("\ncibles du test absentes du dictionnaire:", len(missing), "/", len(tg))
print("  ", missing)
print("\nfrequences de quelques cibles ratees:")
for t in ["bibliothèque", "rivière", "forêt", "étoiles", "dorée", "d'une", "l'eau", "l'été", "l'aube", "s'allumaient", "noyé", "toits", "soir", "bruit", "personne", "lampe", "salle", "tours", "verger", "dit", "disaient"]:
    print(f"  {t:14s}", words.get(t, "ABSENT")[:1])
# parasites : noms propres / anglais evidents
suspects = ["neely", "benny", "salinger", "smith", "fans", "kda", "blair", "marty", "mary", "selena", "depp", "ubu", "abd", "ruth", "roth", "rory", "peter", "pieter", "côme", "léa", "céline", "delonge", "madison", "lé", "dz", "kz", "zr", "uk", "lr", "rr", "ee", "eb", "ev", "ij", "rt", "qin", "æquo"]
print("\nparasites presents (mot -> f):")
for s in suspects:
    if s in words: print(f"  {s}: f={words[s][0]} {words[s][1][:30]}")
# distribution de frequence
fs = sorted((v[0] for v in words.values()), reverse=True)
print("\nfreq: max", fs[0], "médiane", fs[len(fs)//2], "min", fs[-1])
low = [w for w, v in words.items() if len(w) <= 2]
print("mots <=2 lettres:", len(low), low[:80])
