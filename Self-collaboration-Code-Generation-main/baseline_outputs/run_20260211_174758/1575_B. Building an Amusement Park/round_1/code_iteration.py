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
    
    # Precompute distances and angles
    dists = []
    angles = []
    for (x, y) in points:
        d = math.hypot(x, y)
        theta = math.atan2(y, x)
        dists.append(d)
        angles.append(theta)
    
    EPS = 1e-9
    # Binary search on radius
    lo, hi = 0.0, 400000.0  # 2*10^5 is enough, but use 4e5 for safety
    for _ in range(60):
        mid = (lo + hi) / 2.0
        r = mid
        
        intervals = []
        for i in range(n):
            d = dists[i]
            # Special case: point at origin
            if abs(d) < EPS:
                intervals.append((0.0, 2 * math.pi))
                continue
            # If point is too far away
            if d > 2 * r + EPS:
                continue
            # Compute angular interval
            cos_val = d / (2 * r)
            if cos_val > 1.0:
                cos_val = 1.0
            if cos_val < -1.0:
                cos_val = -1.0
            delta = math.acos(cos_val)
            theta = angles[i]
            left = theta - delta
            right = theta + delta
            # Normalize to [0, 2π)
            if left < 0:
                left += 2 * math.pi
                right += 2 * math.pi
            intervals.append((left, right))
        
        # Sweep line to check coverage >= k
        events = []
        for left, right in intervals:
            events.append((left, 1))
            events.append((right, -1))
            # Add shifted copy for wrap-around
            events.append((left + 2 * math.pi, 1))
            events.append((right + 2 * math.pi, -1))
        
        events.sort()
        cnt = 0
        feasible = False
        for _, typ in events:
            cnt += typ
            if cnt >= k:
                feasible = True
                break
        
        if feasible:
            hi = mid
        else:
            lo = mid
    
    print(f"{hi:.10f}")