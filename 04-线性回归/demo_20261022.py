def s(t):
    u = 2 * t + 5
    return u * u

for h in (1, 0.1, 0.01, 0.001):
    print(h, (s(1 + h) - s(1)) / h)

for t in (1, 2, 3, 4, 5, 6):
    h = 0.001
    print(t, (s(t + h) - s(t)) / h)







def u(t):
    return 2 * t + 5

def s(u):
    return u * u

h = 0.001
print('u 变多快:', (u(1 + h) - u(1)) / h)
print('s 变多快:', (s(7 + h) - s(7)) / h)