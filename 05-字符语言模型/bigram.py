"""字符级 bigram 计数模型：不用梯度，只数数。

P(下一个字符 | 当前字符) 直接用相邻字符的出现次数估计。
"""

import random
from pathlib import Path

PATH = Path(__file__).with_name('data') / 'tinyshakespeare.txt'

text = PATH.read_text(encoding='utf-8')
chars = sorted(set(text))
stoi = {c: i for i, c in enumerate(chars)}
itos = {i: c for c, i in stoi.items()}
V = len(chars)

# counts[a][b] = 字符 a 后面紧跟字符 b 的次数
counts = [[0] * V for _ in range(V)]
for a, b in zip(text, text[1:]):
    counts[stoi[a]][stoi[b]] += 1

# 每一行归一化成概率 P(b | a)
probs = []
for row in counts:
    total = sum(row)
    probs.append([n / total if total else 1.0 / V for n in row])


def sample(n=300, start='\n', seed=0):
    """按 P(next | current) 逐字符采样。"""
    rng = random.Random(seed)
    i = stoi[start]
    out = [start]
    for _ in range(n - 1):
        i = rng.choices(range(V), weights=probs[i])[0]
        out.append(itos[i])
    return ''.join(out)


def uniform(n=300, seed=0):
    """对照组：每个字符等概率乱抽。"""
    rng = random.Random(seed)
    return ''.join(rng.choice(chars) for _ in range(n))


if __name__ == '__main__':
    print(f'语料 {len(text):,} 字符，字符表大小 {V}')
    print('\n=== 对照组：均匀随机 ===')
    print(uniform(300))
    print('\n=== bigram 计数模型 ===')
    print(sample(300))
