with open("data.txt", encoding="utf-8") as f:
    lines = []
    for line in f:
        lines.append(line.rstrip("\n"))

    max_count = 0
    max_char = None
    counts = {}
    for line in lines:
        for char in line:
            if max_char is None:
                max_char = char
            counts[char] = counts.get(char, 0) + 1
            if max_count < counts[char]:
                max_char = char
                max_count = counts[char]
    print(f"不同字符的种数：{len(counts.keys())}")
    print(f"出现最多的字符：{max_char}, 出现的次数{max_count}")
    big_char = []
    for key in counts.keys():
        if counts[key] >= 10:
            big_char.append(key)

    print(f"出现次数>=10 的字符串列表{big_char}")