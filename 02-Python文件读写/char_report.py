# 一份完整的小脚本：读文件 -> 处理 -> 打印
# 运行方式：先 cd 到这个目录，再 python3 char_report.py

# ---------- ① 读文件 ----------
with open("data.txt", encoding="utf-8") as f:
    text = f.read()

# ---------- ② 处理：字符串方法 + 列表推导式 ----------
words = text.split()                                  # 按空白切分，得到单词列表
cleaned = [w.strip(".,!?").lower() for w in words]    # 列表推导式：逐个去标点、转小写
lengths = [len(w) for w in cleaned]                   # 再遍历一次，取每个词的长度

# ---------- ③ 打印 ----------
print("总词数:", len(cleaned))
print("平均长度:", sum(lengths) / len(lengths))
print("长度 >= 5 的词:", [w for w in cleaned if len(w) >= 5])
