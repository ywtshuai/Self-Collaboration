import sys
import math

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
    
    EPS = 1e-12
    TWO_PI = 2.0 * math.pi
    
    # Binary search on radius
    lo, hi = 0.0, 400000.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        r = mid
        
        intervals = []
        for i in range(n):
            d = dists[i]
            # Special case: point at origin
            if abs(d) < EPS:
                intervals.append((0.0, TWO_PI))
                continue
            # If point is too far away
            if d > 2 * r + EPS:
                continue
            # Compute angular interval
            cos_val = d / (2 * r)
            cos_val = max(-1.0, min(1.0, cos_val))
            delta = math.acos(cos_val)
            theta = angles[i]
            left = theta - delta
            right = theta + delta
            
            # Handle full circle case
            if right - left >= TWO_PI - EPS:
                intervals.append((0.0, TWO_PI))
                continue
            
            # Normalize to [0, 2π)
            left = math.fmod(left, TWO_PI)
            if left < 0:
                left += TWO_PI
            right = math.fmod(right, TWO_PI)
            if right < 0:
                right += TWO_PI
            
            if left <= right + EPS:
                intervals.append((left, right))
            else:
                # Wraps around
                intervals.append((left, TWO_PI))
                intervals.append((0.0, right))
        
        # Sweep line to check coverage >= k
        events = []
        for left, right in intervals:
            events.append((left, 1))
            events.append((right, -1))
            # Add shifted copy for circular coverage
            events.append((left + TWO_PI, 1))
            events.append((right + TWO_PI, -1))
        
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

if __name__ == "__main__":
    solve()