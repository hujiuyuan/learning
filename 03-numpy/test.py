import numpy as np

# 1) 建一个 0 到 11 的一维数组（12 个数字），叫 b
b = np.arange(0, 12)
# 2) 打印 b 的形状
print(b.shape)
# 3) 用 reshape 把它变成 3 行 4 列，结果叫 c
c = b.reshape(3, 4)
# 4) 打印 c 的形状
print(c.shape)
# 5) 打印「第 2 行、第 3 列」那个数字
print(c[1][2])
print(c[1, 2])
print(c[1:2, 2:3])