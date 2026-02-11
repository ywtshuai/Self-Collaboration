def solve() -> None:
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    k = int(next(it))
    points = []
    for _ in range(n):
        x = int(next(it))
        y = int(next(it))
        points.append((x, y))
    
    if k == 1:
        print("0.0000000000")
        return
    
    # Binary search on radius r
    low, high = 0.0, 4e5  # Upper bound can be up to 2e5, but use 4e5 for safety
    eps = 1e-7
    
    for _ in range(60):  # Fixed number of iterations for precision
        mid = (low + high) * 0.5
        r = mid
        
        if r < 1e-12:
            # Special case: very small radius
            cnt = 0
            for x, y in points:
                if abs(x) < 1e-12 and abs(y) < 1e-12:
                    cnt += 1
            if cnt >= k:
                high = mid
            else:
                low = mid
            continue
        
        events = []
        origin_count = 0
        
        for x, y in points:
            d = math.hypot(x, y)
            if d < 1e-12:
                origin_count += 1
                continue
            if d > 2 * r + 1e-12:
                continue
            
            angle = math.atan2(y, x)
            half_width = math.acos(min(1.0, d / (2 * r)))
            start = angle - half_width
            end = angle + half_width
            
            # Normalize to [0, 2π)
            if start < 0:
                start += 2 * math.pi
                end += 2 * math.pi
            
            events.append((start, 1))
            events.append((end, -1))
            # Add wrapped copy
            events.append((start + 2 * math.pi, 1))
            events.append((end + 2 * math.pi, -1))
        
        # Sort events
        events.sort()
        
        # Sweep line
        cur = origin_count
        possible = False
        for _, typ in events:
            cur += typ
            if cur >= k:
                possible = True
                break
        
        if possible:
            high = mid
        else:
            low = mid
    
    # Output with sufficient precision
    print(f"{low:.10f}")