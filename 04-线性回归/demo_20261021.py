import numpy as np

x = np.array([1., 2.])
y = np.array([2., 4.])

w = 3.0
alpha = 0.1

for step in range(20):
    y_pred = w * x
    # print(f'y_pred({y_pred}) = w({w}) * x({x})')
    err = y_pred - y
    J = (err ** 2).sum() / (2 * 2)
    grad = (err * x).sum() / 2
    w = w - alpha * grad
    print(f'step {step:>2}  w = {w:.4f}  J = {J:.4f}')