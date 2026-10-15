# 循环
fruits = ["apple", "banana", "cherry"]
# for-each 循环，类似java for(var i : list)
for fruit in fruits:
    print(fruit)

# 带下标的循环， 类java for(int i = 0;i < fruits.size(); i++)
for i, fruit in enumerate(fruits):
    print(i, fruit)

# range 循环（左闭右开），类似java for(int i = 0; i < 10; i++)
for i in range(10):
    print(i) # 输出 0~9
    # if i == 2:
    #     continue # continue 的用法和java类似
    # if i == 3:
    #     break # break 的用法和java类似

for i in range(1, 10):
    print(i) # 输出1~9

# while 循环, 和 java while(){} 类似
n = 3
while n > 0:
    print(n)
    n -= 1

# 三个参数：start, stop, step
for i in range(0, 10, 2):    # 0 2 4 6 8
    print(i)
for i in range(10, 0, -1):   # 10 9 8 ... 1 倒序
    print(i)