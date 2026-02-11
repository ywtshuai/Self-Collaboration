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
        cnt[0][0] = 1
        sum_h[0][0] = a[centroid] % MOD
        
        for to, first_col in adj[centroid]:
            if removed[to]:
                continue
            
            # collect all paths in this subtree
            paths = []  # (switches, last_color, happiness, count)
            
            stack = [(to, centroid, first_col, 0, a[to] + a[centroid], first_col)]
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
                            contribution = (total_h * c1) % MOD
                            contribution = (contribution * c2) % MOD
                            ans = (ans + contribution) % MOD
            
            # add current subtree paths to cnt/sum_h
            for sw, col, h, c in paths:
                cnt[sw][col] = (cnt[sw][col] + c) % MOD
                sum_h[sw][col] = (sum_h[sw][col] + h) % MOD
        
        # add paths where centroid is one endpoint
        total_h_all = 0
        for sw in range(k+1):
            for col in range(2):
                total_h_all = (total_h_all + sum_h[sw][col]) % MOD
        # subtract centroid itself (already counted as single vertex)
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