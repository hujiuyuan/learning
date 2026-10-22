def s(t):
    return 5*t*t

for t in (1, 2, 3, 4, 5, 6):
    h = 0.001
    print(t, (s(t + h) - s(t)) / h)