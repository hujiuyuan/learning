# 三种写法的对照：块里抛异常时，文件到底关了没有？

print("=== A：用 with，块里抛异常 ===")
f = None
try:
    with open("data.txt", encoding="utf-8") as f:
        f.read()
        raise RuntimeError("故意炸一下")
except RuntimeError as e:
    print("捕获到:", e)
print("f.closed =", f.closed)

print()
print("=== B：不用 with，块里抛异常（老写法） ===")
f2 = None
try:
    f2 = open("data.txt", encoding="utf-8")
    f2.read()
    raise RuntimeError("故意炸一下")
except RuntimeError as e:
    print("捕获到:", e)
print("f2.closed =", f2.closed)

print()
print("=== C：不用 with，但自己写 try/finally ===")
f3 = None
try:
    f3 = open("data.txt", encoding="utf-8")
    f3.read()
    raise RuntimeError("故意炸一下")
except RuntimeError as e:
    print("捕获到:", e)
finally:
    f3.close()
print("f3.closed =", f3.closed)
