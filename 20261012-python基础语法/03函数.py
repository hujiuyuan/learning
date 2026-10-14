def add(a, b):
    return a + b

# 默认参数
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}"

# 关键字参数调用
print(greet("Bob", greeting="Hi"))

# 返回多个值（其实就是元组）
def min_max(nums):
    return min(nums), max(nums)

lo, hi = min_max([3, 1, 4, 1, 5])

# 没有重载，没有 void —— 不写 return 就返回 None
def log(msg):
    print(msg)

log(log(lo))