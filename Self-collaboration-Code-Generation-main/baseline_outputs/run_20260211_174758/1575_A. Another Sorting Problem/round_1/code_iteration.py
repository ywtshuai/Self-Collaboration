def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    
    n = int(data[0])
    m = int(data[1])
    strings = data[2:2+n]
    
    # Transform each string into a tuple for comparison
    transformed = []
    for idx, s in enumerate(strings, 1):
        # For odd positions (1-based): use original char value
        # For even positions (1-based): use complement ('Z' - char) so that
        # ascending order of complement corresponds to descending order of original
        t = tuple(
            ord(c) if (i % 2 == 0) else (ord('Z') - ord(c))
            for i, c in enumerate(s)
        )
        transformed.append((t, idx))
    
    # Sort by transformed tuple
    transformed.sort(key=lambda x: x[0])
    
    # Output indices
    indices = [str(idx) for _, idx in transformed]
    print(' '.join(indices))