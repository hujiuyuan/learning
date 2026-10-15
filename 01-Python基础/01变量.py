# 相当于是 java 的 String，不需要写类型
name = "Alice"
# 相当于是 java 的 int 类型
age = 30
# 相当于是 java 的 double 类型（精度64位），float类型用 numpy 包的 numpy.float32（精度32位）
score = 92.5
# 相当于是 java 的 boolean 类型
is_ok = True
# 相当于是 java 的 null
nothing = None

# 类型转换
# 字符串 转 数字
n = int("12")
# 数字转换字符串
s = str(age)

# 多重赋值
a,b = 1,2
#多重交换
a,b = b,a

# 额外学习 打印到控制台，f-string 的拼接方式，相当于是 java 的 System.out.println
print(f"{name} is {age} , score={score}")

# 数字类型比较大小不能用 ==，应该用 math 包的 isclose 方法, 返回结果是boolean类型
import math
print(math.isclose(age, score))