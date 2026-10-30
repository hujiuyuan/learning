def J(w):
    return (w - 2) ** 2


def dJ(w):
    return 2 * (w - 2)


def run(lr, steps=20):
    w = 3.0
    trace = []
    for _ in range(steps):
        w = w - lr * dJ(w)
        trace.append(w)
    return trace


if __name__ == '__main__':
    marks = (1, 2, 3, 5, 10, 20)
    print(f'{"lr":>5} | ' + ' | '.join(f'step {m:>2}' for m in marks) + ' | 最后 J')
    print('-' * 78)
    for lr in (0.01, 0.1, 0.5, 0.9, 1.0, 1.1):
        t = run(lr)
        cells = ' | '.join(f'{t[m - 1]:8.4f}' for m in marks)
        print(f'{lr:>5} | {cells} | {J(t[-1]):9.4f}')
