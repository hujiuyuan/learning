"""第 5 节的实测脚本：axis / 广播 / @ 矩阵乘法

配合 [[numpy用法]] 第 8～10 节看。直接运行：

    python3 broadcast_demo.py
"""
import numpy as np

a = np.array([[0, 1, 2],
              [3, 4, 5]])          # 形状 (2, 3)
print('a ='); print(a, '  a.shape =', a.shape)
print()

print('--- axis：让某一维消失 ---')
print('a.sum(axis=0) =', a.sum(axis=0), '  形状', a.sum(axis=0).shape, '  <- 行消失，每列一个数')
print('a.sum(axis=1) =', a.sum(axis=1), '  形状', a.sum(axis=1).shape, '  <- 列消失，每行一个数')
print('a.sum()       =', a.sum(), '                <- 全压掉，一个数')
print('取数不是运算：a[0] =', a[0], '  <- 本来就在的那一行')
print()

print('--- 广播：两个形状不一样怎么配 ---')
print('a + 10  ->'); print(a + 10, '  形状', (a + 10).shape, ' <- 每格加 10')
print('a + [10, 20, 30]  ->'); print(a + [10, 20, 30], '  形状', (a + [10, 20, 30]).shape, ' <- 按列配')
print('a + [[100], [200]]  ->'); print(a + [[100], [200]], '  形状', (a + [[100], [200]]).shape, ' <- 按行配')
print()
print('a + [10, 20]  -> 配不上：')
try:
    a + [10, 20]
except ValueError as e:
    print('   ValueError:', e)
print()

print('--- 最容易混的：(3,) 和 (3,1) 到底是什么 ---')
one_d = np.array([1, 2, 3])
two_d = np.array([[1], [2], [3]])
print('np.array([1, 2, 3])           shape', one_d.shape, ' ndim', one_d.ndim, ' 一维')
print('np.array([[1], [2], [3]])     shape', two_d.shape, ' ndim', two_d.ndim, ' 二维，3 行 1 列')
print('one_d[1] =', one_d[1], '   two_d[1, 0] =', two_d[1, 0])
print()

print('--- @ 矩阵乘法 ---')
A = np.array([[1, 2, 3],
              [4, 5, 6]])          # (2, 3)
B = np.array([[10, 20],
              [30, 40],
              [50, 60]])           # (3, 2)
print('A.shape', A.shape, ' B.shape', B.shape, ' -> 左边 3 列 = 右边 3 行，能乘')
print('A @ B ='); print(A @ B, '  形状', (A @ B).shape, ' <- 取最左和最右 (2,2)')
print('B @ A ='); print(B @ A, '  形状', (B @ A).shape, ' <- 换顺序，连形状都变了')
print()
print('逐格验算 A @ B 的第 1 行第 1 列：1*10 + 2*30 + 3*50 =', 1*10 + 2*30 + 3*50)
print()

print('--- @ 和 sum 的关系：矩阵乘法是「带权重的求和」 ---')
print('a.sum(axis=1)                =', a.sum(axis=1), '  形状', a.sum(axis=1).shape)
print('a @ [[1],[1],[1]]            ='); print(a @ np.array([[1], [1], [1]]), '  形状', (a @ np.array([[1], [1], [1]])).shape)
print('  值一样，形状差一维：(2,) vs (2,1)')
print()

print('--- @ 和 * 不是一回事 ---')
print('A * B 会怎样：', end='')
try:
    A * B
except ValueError as e:
    print('报错（形状不同，广播也配不上）:', str(e)[:60], '...')
D = np.array([[1, 2], [3, 4]])
E = np.array([[10, 20], [30, 40]])
print('D * E  (逐格乘) ='); print(D * E)
print('D @ E  (矩阵乘法) ='); print(D @ E)
