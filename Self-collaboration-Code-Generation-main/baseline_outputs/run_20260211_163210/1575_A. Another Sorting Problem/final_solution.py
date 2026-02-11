import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    
    n = int(data[0])
    m = int(data[1])
    strings = data[2:]
    
    # Create list of (key, original_index)
    indexed_strings = []
    for i in range(n):
        s = strings[i]
        # Build key: odd positions (1-based) -> normal value, even positions -> negative value
        key = []
        for j in range(m):
            if j % 2 == 0:  # odd position (1-based)
                key.append(ord(s[j]))
            else:  # even position (1-based)
                key.append(-ord(s[j]))
        indexed_strings.append((tuple(key), i + 1))
    
    # Sort by the custom key
    indexed_strings.sort(key=lambda x: x[0])
    
    # Output original indices
    result = [str(idx) for _, idx in indexed_strings]
    print(' '.join(result))

if __name__ == "__main__":
    main()