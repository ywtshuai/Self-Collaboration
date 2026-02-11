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
    low, high = 0.0, 2e5
    eps = 1e-7
    while high - low > eps:
        mid = (low + high) * 0.5
        r = mid
        
        events = []
        cnt = 0
        for x, y in points:
            d = math.hypot(x, y)
            if d > 2 * r + 1e-12:
                continue
            if abs(d) < 1e-12:
                # point at origin: always inside for any center
                cnt += 1
                continue
            angle = math.atan2(y, x)
            half_width = math.acos(d / (2 * r))
            start = angle - half_width
            end = angle + half_width
            # wrap to [0, 2π)
            if start < 0:
                start += 2 * math.pi
                end += 2 * math.pi
            events.append((start, 1))
            events.append((end, -1))
            # add wrapped interval
            events.append((start + 2 * math.pi, 1))
            events.append((end + 2 * math.pi, -1))
        
        # sort events
        events.sort()
        # sweep
        cur = cnt
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
    
    print(f"{low:.10f}")