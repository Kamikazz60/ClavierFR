"""Modifie les réglages de scoring de l'entrée « encodeur + LM hungry_jellyfish » dans libswipe_jni.so (toutes ABI) de l'AAR.
Usage : python patch_aar.py alpha beta gamma lambda [gamma_prune beta_prune]   ('-' = inchangé). Part toujours de futo-swipe-release.aar.orig."""
import sys, zipfile, re
ORIG = r"C:\Users\Doanh\Desktop\Programme IA\clavierPers\futo-swipe-release.aar.orig"
DST = r"C:\Users\Doanh\Desktop\Programme IA\clavierPers\futo-keyboard\libs\futo-swipe-release.aar"
KEY = b'"encoder:honorable_sturgeon contextlm:hungry_jellyfish"'
names = ["alpha", "beta", "gamma", "lambda", "gamma_prune", "beta_prune"]
vals = dict(zip(names, sys.argv[1:7]))
def patch(d):
    i = d.find(KEY); assert i >= 0
    j = d.index(b"}", i); blk = d[i:j]
    for n, v in vals.items():
        if v == "-": continue
        m = re.search(rb'("%s":\s*)([0-9.]+)' % n.encode(), blk); assert m, n
        new = ("%.4f" % float(v)).encode()
        assert len(new) == len(m.group(2)), (n, v, m.group(2))
        blk = blk[:m.start(2)] + new + blk[m.end(2):]
    return d[:i] + blk + d[j:]
zin = zipfile.ZipFile(ORIG); zout = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zin.infolist():
    data = zin.read(it.filename)
    if it.filename.endswith("libswipe_jni.so"): data = patch(data)
    zout.writestr(it, data)
zout.close(); print("AAR patché :", {k: v for k, v in vals.items() if v != "-"})
