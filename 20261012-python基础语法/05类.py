class CharVocab:
    def __init__(self):
        self.chars = []
        self.stoi = {}
    def build(self, text):
        for ch in text:
            if ch not in self.stoi:
                self.stoi[ch] = len(self.chars)
                self.chars.append(ch)

    def encode(self, text):
        out = []
        for ch in text:
            out += [self.stoi[ch]]
        return out

    def decode(self, ids):
        out = ""
        for ch in ids:
            out += self.chars[ch]
        return out

v = CharVocab()
v.build("deepseek")
print(v.chars)          # 期望 ['d', 'e', 'p', 's', 'k']
print(v.stoi)           # 期望 {'d': 0, 'e': 1, 'p': 2, 's': 3, 'k': 4}
print(v.encode("seed")) # 期望 [3, 1, 1, 0]
print(v.decode([0, 1, 2]))   # 期望 'dep'


