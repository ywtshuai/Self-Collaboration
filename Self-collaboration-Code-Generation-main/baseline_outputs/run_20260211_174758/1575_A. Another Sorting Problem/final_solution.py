import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    
    n = int(data[0])
    m = int(data[1])
    strings = data[2:2+n]
    
    transformed = []
    for idx, s in enumerate(strings, 1):
        t = tuple(
            ord(c) if (i % 2 == 0) else (ord('Z') - ord(c))
            for i, c in enumerate(s)
        )
        transformed.append((t, idx))
    
    transformed.sort(key=lambda x: x[0])
    
    indices = [str(idx) for _, idx in transformed]
    print(' '.join(indices))

if __name__ == "__main__":
    main()