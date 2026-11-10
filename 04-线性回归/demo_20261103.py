import numpy as np

def J(w):
      return (w - 2)**2

def grad(w):
      return 2*(w - 2)

w0 = 10.0
for lr in [0.01, 0.1, 1.0, 1.1]:
    w = w0
    print(f"\nlr = {lr}")
    for step in range(10):
      g = grad(w)
      w = w - lr * g
      print(f"step {step+1:2d}: w = {w:10.4f}, J = {J(w):12.4f}")