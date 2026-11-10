import numpy as np

text = "hello world"
vocab = sorted(set(text))
char_to_idx = {ch: i for i, ch in enumerate(vocab)}

chars = list(text)
inputs = chars[:-1]
targets = chars[1:]
n, V = len(inputs), len(vocab)

X = np.zeros((n, V))
for row, ch in enumerate(inputs):
    X[row, char_to_idx[ch]] = 1

print("vocab:", vocab)
print("V =", V)
print("n =", n)
print("X.shape =", X.shape)
print(X)
print(X[:3])

import numpy as np

text = "abca"
vocab = sorted(set(text))
char_to_idx = {ch: i for i, ch in enumerate(vocab)}
idx_to_char = {i: ch for ch, i in char_to_idx.items()}

chars = list(text)
inputs = chars[:-1]
targets = chars[1:]
n, V = len(inputs), len(vocab)

X = np.zeros((n, V))
for row, ch in enumerate(inputs):
    X[row, char_to_idx[ch]] = 1

print("vocab:", vocab)
print("V =", V)
print("n =", n)
print("inputs:", inputs)
print("targets:", targets)
print("X.shape =", X.shape)
print(X)