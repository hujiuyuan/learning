"""第 5 节动手练习：改数字，跑一遍，看输出

用法：
    1. 按注释里的 TODO 改数字（一次改一个，改完就运行一次）
    2. 运行： python3 练习-改数字.py
    3. 看输出有没有按你预期变

不用推理，看到什么就是什么。
"""
import numpy as np

# ===== 第 0 步：先什么都不改，跑一次，看输出 =====

a = np.array([[0, 1, 2],
              [3, 4, 5]])          # 形状 (2, 3)：2 行 3 列
print('a.shape =', a.shape)
print(a)
print()

# ----- 1. axis：改一改，看结果怎么变 -----
# 口诀①：axis=0 往下合、axis=1 往右合；数字是第几维，那一维消失

print('a.sum(axis=0) =', a.sum(axis=0), '  形状', a.sum(axis=0).shape)
print('a.sum(axis=1) =', a.sum(axis=1), '  形状', a.sum(axis=1).shape)
print()
# TODO 1: 把上面两行的 axis 互换（0 变 1、1 变 0），再跑一次，看输出的数字和形状怎么变
print(f'a.sum(axis=1) = {a.sum(axis=1)}, 形状：{a.sum(axis=1).shape}')
print(f'a.sum(axis=0) = {a.sum(axis=0)}, 形状：{a.sum(axis=0).shape}')
print('-------------')
# TODO 2: 把 a 改成 3 行 4 列（自己填 12 个数字），再跑一次，看两个形状分别变成什么
# a = np.arange(12).reshape(3, 4) # 修改A数组会导致下面第二节广播报错先注释
print(f'a.sum(axis=1) = {a.sum(axis=1)}, 形状：{a.sum(axis=1).shape}')
print(f'a.sum(axis=0) = {a.sum(axis=0)}, 形状：{a.sum(axis=0).shape}')
print('-------------')

# ----- 2. 广播：改加数，看哪些能算、哪些报错 -----
# 口诀②：+ - * / 从右往左对齐；最右那位必须相等，或者是 1

b = np.array([10, 20, 30])           # 形状 (3,)
print('b.shape =', b.shape, ' b =', b)
print('a + b =')
print(a + b)                          # (2,3) 加 (3,)：最右 3 对 3 ✓
print()
# TODO 3: 把 b 改成 [10, 20]（两行那个数字），跑一次，看报错信息怎么写
# b = np.reshape(b,(2, )) # ValueError: cannot reshape array of size 3 into shape (2,)
# TODO 4: 把 b 改回 3 个数，但写成竖着的 [[10],[20],[30]]，跑一次，看会怎样
#         （提示：竖着写就是二维 (3,1)，中间加一层方括号）
# b = np.reshape(b,(3,1))  # 试过：a(2,3) + b(3,1) -> ValueError: operands could not be broadcast together with shapes (2,3) (3,1)
#                          # 原因：竖着写是二维，那个 3 对上的是行方向，而 a 只有 2 行
print('b.shape =', b.shape, ' b =', b)
print(f'a + b = {a+b}')
print()

# ----- 3. @ 矩阵乘法：改形状，看什么时候能乘 -----
# 口诀④：中间位相等才能乘；结果取最左 + 最右；每格 = 左边一整行 · 右边一整列

w = np.array([[1],
              [1],
              [1]])                  # 形状 (3, 1)
print('w.shape =', w.shape)
print('a @ w =')
print(a @ w)                          # (2,3) @ (3,1)：中间 3 对 3 ✓ 结果 (2,1)
print('a.sum(axis=1) =', a.sum(axis=1), '  形状', a.sum(axis=1).shape)
print('   ↑ 值一样，形状不同：(2,1) vs (2,)')
print()
# TODO 5: 把 w 改成 (3, 2)（3 行 2 列），跑一次，看结果形状变成什么
# w = np.reshape(w, (3,2)) # 报错 无法改成 3行 2 列
print('w.shape =', w.shape, ' w =', w)
print()

# ----- 4. 一维还是二维：看打印的样子 -----
# 口诀③：形状里 1 个数字是一维（不分行列），2 个数字才是几行几列

one_d = np.array([1, 2, 3])
two_d = np.array([[1], [2], [3]])
print('np.array([1, 2, 3])        shape', one_d.shape, ' ndim', one_d.ndim)
print(one_d)
print('np.array([[1], [2], [3]])  shape', two_d.shape, ' ndim', two_d.ndim)
print(two_d)
