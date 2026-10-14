# 列表相当于是ArrayList
# 改原对象：append / sort / a[0] = / +=
a = [1, 2]; b = a; a.append(9)      # b 也变，[1, 2, 9]
a = [1, 2]; b = a; a += [3]         # b 也变，[1, 2, 3]  ← += 是雷
# 换新对象：+ / 切片 / sorted
a = [1, 2]; b = a; a = a + [3]      # b 不变，还是 [1, 2]
# 切片左闭右开，跟 range 一样

# 字典相当于是 LinkedHashMap，有序，底层原理是否一致不太清楚
