import numpy as np

sales = np.array([[50, 60, 70],    # 商品 尺码 A
                  [40, 50, 60],    # 商品 尺码 B
                  [30, 20, 40],    # 商品 尺码 C
                  [80, 70, 90]])   # 商品 尺码 D

print('sales.shape =', sales.shape)

# ① 每个门店的总销量（把 4 个商品合起来，一个门店一个数）
store_total = sales.sum(axis=0)

print('每店总销量 =', store_total)
print('shape =', store_total.shape)