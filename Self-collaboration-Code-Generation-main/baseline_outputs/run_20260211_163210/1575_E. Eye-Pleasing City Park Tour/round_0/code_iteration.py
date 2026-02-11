def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    k = int(next(it))
    a = [0] * n
    for i in range(n):
        a[i] = int(next(it))
    
    adj = [[] for _ in range(n)]
    for _ in range(n-1):
        u = int(next(it)) - 1
        v = int(next(it)) - 1
        t = int(next(it))
        adj[u].append((v, t))
        adj[v].append((u, t))
    
    # centroid decomposition
    removed = [False] * n
    subtree_size = [0] * n
    
    def dfs_size(v, p):
        subtree_size[v] = 1
        for to, _ in adj[v]:
            if to != p and not removed[to]:
                dfs_size(to, v)
                subtree_size[v] += subtree_size[to]
    
    def find_centroid(v, p, total):
        for to, _ in adj[v]:
            if to != p and not removed[to] and subtree_size[to] * 2 > total:
                return find_centroid(to, v, total)
        return v
    
    ans = 0
    
    # single vertex paths
    for val in a:
        ans = (ans + val) % MOD
    
    # paths through centroid
    def process_centroid(centroid):
        nonlocal ans
        # cnt[sw][col] = number of paths from centroid to some vertex
        # sum_h[sw][col] = total happiness sum of those paths
        cnt = [[0, 0] for _ in range(k+2)]
        sum_h = [[0, 0] for _ in range(k+2)]
        
        # start with centroid itself (path of length 0)
        cnt[0][0] = 1  # color doesn't matter for length 0, use 0 as default
        sum_h[0][0] = a[centroid] % MOD
        
        for to, col in adj[centroid]:
            if removed[to]:
                continue
            
            # collect all paths in this subtree
            paths = []  # (switches, last_color, happiness, count)
            
            stack = [(to, centroid, col, 1, a[to], col)]
            while stack:
                v, p, last_col, sw, happiness, first_col = stack.pop()
                # record this path
                if sw <= k:
                    paths.append((sw, last_col, happiness % MOD, 1))
                # continue DFS
                for nxt, edge_col in adj[v]:
                    if nxt == p or removed[nxt]:
                        continue
                    new_sw = sw + (1 if edge_col != last_col else 0)
                    new_happiness = happiness + a[nxt]
                    stack.append((nxt, v, edge_col, new_sw, new_happiness, first_col))
            
            # combine with previous subtrees
            for sw1, col1, h1, c1 in paths:
                for sw2 in range(k+1):
                    for col2 in range(2):
                        c2 = cnt[sw2][col2]
                        if c2 == 0:
                            continue
                        total_sw = sw1 + sw2
                        if col1 != col2:
                            total_sw += 1
                        if total_sw <= k:
                            # happiness contribution: (h1 + h2 - a[centroid]) * c1 * c2
                            h2 = sum_h[sw2][col2]
                            total_h = (h1 + h2 - a[centroid]) % MOD
                            contribution = (total_h * c1 % MOD) * c2 % MOD
                            ans = (ans + contribution) % MOD
            
            # add current subtree paths to cnt/sum_h
            for sw, col, h, c in paths:
                cnt[sw][col] = (cnt[sw][col] + c) % MOD
                sum_h[sw][col] = (sum_h[sw][col] + h) % MOD
        
        # also count paths that start at centroid and go into one subtree
        # (these were counted as single vertex already, but we need paths of length >=1)
        # Actually, single vertex is already counted at the beginning.
        # For paths from centroid to some vertex in a subtree:
        # They are valid if switches <= k
        # Their contribution is the path happiness * 1 (paired with centroid as other endpoint)
        # But careful: we already counted single vertex paths.
        # Let's count paths where the other endpoint is centroid itself:
        # That's just the single vertex path, already counted.
        # So we need paths where both endpoints are not centroid? Actually in our combine step
        # we already counted all pairs from different subtrees, which includes paths where
        # one endpoint is centroid? Wait, centroid is the "center" but not necessarily endpoint.
        # In centroid decomposition, we consider paths passing through centroid.
        # A path from centroid to vertex v in subtree S: this path has one endpoint at centroid.
        # When we combine with "empty path from centroid" (which is in cnt), we get
        # paths from centroid to v. But we must not double count single vertex.
        # Actually, we should count all paths with centroid as one endpoint separately.
        # Let's do that now:
        for sw in range(k+1):
            for col in range(2):
                c = cnt[sw][col]
                if c == 0:
                    continue
                # paths from centroid to some vertex (including centroid itself)
                # but subtract the centroid itself which was counted as single vertex
                if sw == 0 and col == 0:
                    # this is the centroid itself (path length 0)
                    # we already counted it, so skip
                    pass
                else:
                    h = sum_h[sw][col]
                    # contribution: happiness sum of path * 1 (other endpoint is centroid)
                    # Actually, for path (centroid, v), f(centroid,v) = h
                    # We need to count it once (since u<=v, and centroid <= v or v <= centroid?)
                    # Since we consider all pairs u<=v, we should count both (centroid,v) and (v,centroid)
                    # But our total sum is over u<=v, so if centroid != v, we count only one of them.
                    # However, in the problem, f(u,v) is defined for u≤v.
                    # So for centroid != v, we need to know if centroid < v or v < centroid.
                    # That's messy. Better to count all ordered pairs (u,v) with u<=v.
                    # Let's think differently: In centroid decomposition, when we process centroid C,
                    # we consider all paths passing through C. A path (u,v) with u<v that passes through C
                    # will be counted exactly once when C is the first centroid on that path.
                    # So we should count all such paths where C is the "highest" centroid.
                    # For paths where C is an endpoint, they also pass through C.
                    # So we should count them here.
                    # The path (C, v) has happiness h (which includes a[C] + ... + a[v]).
                    # We need to add h to answer.
                    # But careful: we already added single vertex paths. So for v=C, skip.
                    # For v≠C, add h.
                    # However, our cnt[sw][col] includes multiple vertices. We need to subtract
                    # the centroid itself which is in cnt[0][0].
                    # Actually easier: just add all h from cnt, then subtract a[C] for the
                    # centroid itself entry.
                    # But wait, h in sum_h[sw][col] is total happiness of all paths from C
                    # to vertices in subtree with given (sw,col). So adding all h gives
                    # sum over v of f(C,v). But we need f(C,v) for v>C? Actually we need
                    # f(C,v) for all v (since C might be less than or greater than v).
                    # Since we sum over u<=v, we should only count pairs where C <= v.
                    # That depends on vertex numbering. This is getting too complex.
                    # Alternative: Count all ordered pairs (u,v) with u<v, then at the end
                    # add single vertices. Then divide by issues...
                    # Let's follow the standard centroid decomposition approach:
                    # We count all unordered pairs (u,v) with u≠v, then add single vertices.
                    # Then we don't care about u<=v, we just need sum of f(u,v) over all unordered pairs.
                    # Since f(u,v) = f(v,u), and we want sum over u<=v, we can compute sum over
                    # all unordered pairs, then add single vertices (f(u,u)=a[u]).
                    # So let's compute sum over all unordered pairs u≠v.
                    # In centroid decomposition, we count each unordered pair exactly once.
                    # So we can just compute sum over all unordered pairs passing through centroid.
                    # For paths where centroid is endpoint, they are also unordered pairs.
                    # So we should count them.
                    # In our combine step, we counted pairs from different subtrees.
                    # That doesn't include pairs where one endpoint is centroid.
                    # So we need to add those separately.
                    # For each path from centroid to v (v≠centroid), the pair is (centroid,v).
                    # Its contribution is h (which includes a[centroid] + ... + a[v]).
                    # So we add h for each such v.
                    # But our cnt includes the centroid itself. So we need to subtract that.
                    # Let's compute total_h_all = sum over all sum_h[sw][col]
                    # Subtract a[centroid] (for the centroid itself)
                    # That gives sum over v≠centroid of f(centroid,v).
                    # Add that to ans.
                    pass
        
        # Actually, let's compute it properly:
        total_h_all = 0
        total_cnt_all = 0
        for sw in range(k+1):
            for col in range(2):
                total_h_all = (total_h_all + sum_h[sw][col]) % MOD
                total_cnt_all = (total_cnt_all + cnt[sw][col]) % MOD
        # total_h_all = sum of happiness of all paths from centroid to some vertex (including centroid)
        # Subtract the centroid itself:
        centroid_contrib = (total_h_all - a[centroid]) % MOD
        ans = (ans + centroid_contrib) % MOD
    
    def decompose(v):
        dfs_size(v, -1)
        cent = find_centroid(v, -1, subtree_size[v])
        process_centroid(cent)
        removed[cent] = True
        for to, _ in adj[cent]:
            if not removed[to]:
                decompose(to)
    
    decompose(0)
    print(ans % MOD)