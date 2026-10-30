import random, subprocess, mgrs
random.seed(7)
m = mgrs.MGRS()
pts = [(60,5),(60,11.9),(75,5),(75,15),(75,25),(75,35),(0,0),(-33.86,151.2),(38.8977,-77.0365),(-79.9,10),(83.9,100),(0.0001,179.9999),(-0.0001,-179.9999),(51.5,-0.0001),(51.5,0.0001),(47.5,6.0),(47.5,5.9999)]
for _ in range(20000):
    pts.append((random.uniform(-79.99,83.99), random.uniform(-180,179.9999)))
inp = "\n".join(f"{a:.7f} {b:.7f}" for a,b in pts)
out = subprocess.run([__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "test_mgrs")], input=inp, capture_output=True, text=True).stdout.split("\n")
bad = 0
for (a,b),o in zip(pts,out):
    a = round(a*1e7)/1e7; b = round(b*1e7)/1e7
    ref = m.toMGRS(a,b,MGRSPrecision=5)
    got = o.replace(" ","")
    if ref != got:
        bad += 1
        if bad <= 10: print("MISMATCH", a, b, ref, got)
print("tested", len(pts), "mismatches", bad)
assert bad <= 40, "too many mismatches"
