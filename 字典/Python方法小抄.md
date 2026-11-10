# Python 方法小抄

项目线「文本 → 词表 → 编号 → one-hot」用到的方法。和 [[Python与Java差异]] 分工：那边只收「照 Java 写会错」的差异，这边收常用写法和参数。

## `set(iterable)`：去重

```python
set("hello")
# {'o', 'l', 'h', 'e'}
```

- 返回一个集合：重复元素只留一个。
- **顺序不保证**，打印出来是什么顺序都可能；要固定顺序就套 `sorted`。
- 空集合写 `set()`，不是 `{}`（`{}` 是空字典）。

## `sorted(iterable)`：排序，返回新列表

```python
sorted(set("hello"))
# ['e', 'h', 'l', 'o']
```

- 不修改原对象，返回一个新 `list`；和 `list.sort()`（原地改）不同。
- 字符串按 **Unicode 编号**从小到大排。英文和空格在 ASCII 范围内，Unicode 与 ASCII 一致；ASCII 是 Unicode 的子集。
- 想按别的规则排，用 `key=`，例如 `sorted(words, key=len)`。

## `enumerate(iterable, start=0)`：同时给编号和元素

```python
list(enumerate(["a", "b", "c"]))
# [(0, 'a'), (1, 'b'), (2, 'c')]
```

- 每次给你 `(编号, 元素)` 两个值，编号默认从 `0` 开始。
- 常用来建映射：

```python
vocab = ["a", "b", "c"]
{ch: i for i, ch in enumerate(vocab)}
# {'a': 0, 'b': 1, 'c': 2}
```

## `ord(ch)`：字符 → Unicode 编号

```python
ord("h")   # 104
ord(" ")   # 32
ord("w")   # 119
```

- 只接受**一个字符**的字符串；`ord("hi")` 会报错。
- 反过来是 `chr(104)` → `'h'`。

## 字典推导式：`{键: 值 for ...}`

```python
vocab = ["a", "b", "c"]
char_to_idx = {ch: i for i, ch in enumerate(vocab)}
idx_to_char = {i: ch for ch, i in char_to_idx.items()}
```

- 不是函数，是 Python 的语法；等价于先建空字典再循环赋值。
- `char_to_idx` 用来编码，`idx_to_char` 用来解码。

## `zip(a, b)`：把两个序列按位置配对

```python
list(zip([1, 2, 3], ["a", "b", "c"]))
# [(1, 'a'), (2, 'b'), (3, 'c')]
```

- 长度不同时，按短的截断。
- 常用来看「输入 → 目标」的样本对。

## 切片：`chars[:-1]`、`chars[1:]`

```python
chars = list("abc")
chars[:-1]   # ['a', 'b']   去掉最后一个
chars[1:]    # ['b', 'c']   去掉第一个
```

- 左闭右开；`[:-1]` 表示从头到倒数第二个。
- 切片返回新列表，不改原列表。

## `len(x)`、`type(x)`

```python
len("hello")        # 5
type("hello")       # <class 'str'>
type(set("hello"))  # <class 'set'>
```

- `len` 是内置函数，不是 `x.length()`。
- `type` 用来看对象到底是什么类型，排查 `set` / `list` / `dict` 混淆时很有用。

## 常见坑

| 坑 | 正解 |
| --- | --- |
| 依赖 `set` 的打印顺序 | `set` 无序；要固定顺序套 `sorted` |
| 以为 `sorted` 改了原列表 | `sorted` 返回新列表；原地排序用 `list.sort()` |
| 把字典推导式当函数 | `{ch: i for ...}` 是语法，不是函数调用 |
| `ord` 传多个字符 | `ord` 只收一个字符；多个字符要逐个取 |
| `{}` 当成空集合 | `{}` 是空字典；空集合写 `set()` |

相关：[[Python与Java差异]]、[[numpy用法]]、[[线性回归与梯度下降]]、[[双线学习地图]]。
