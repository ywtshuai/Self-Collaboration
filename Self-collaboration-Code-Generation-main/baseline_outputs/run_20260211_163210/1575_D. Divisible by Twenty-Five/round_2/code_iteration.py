def solve() -> None:
    s = sys.stdin.readline().strip()
    n = len(s)
    
    # Collect positions
    underscore_pos = []
    x_pos = []
    fixed_digits = list(s)
    
    for i, ch in enumerate(s):
        if ch == '_':
            underscore_pos.append(i)
        elif ch == 'X':
            x_pos.append(i)
        else:
            fixed_digits[i] = ch
    
    # Handle no X case: treat as one X with dummy value
    x_digits = [0] if not x_pos else list(range(10))
    
    count = 0
    
    # Iterate over possible X values
    for x_val in x_digits:
        # Set X positions
        candidate = fixed_digits[:]
        for pos in x_pos:
            candidate[pos] = str(x_val)
        
        # Generate all combinations for underscore positions
        underscore_count = len(underscore_pos)
        
        # Use recursion to generate all combinations
        if underscore_count == 0:
            # No underscores, just check this candidate
            num_str = ''.join(candidate)
            
            # Check leading zero
            if len(num_str) > 1 and num_str[0] == '0':
                continue
            
            # Check divisible by 25
            if len(num_str) >= 2:
                last_two = num_str[-2:]
                if last_two not in ('00', '25', '50', '75'):
                    continue
            else:
                if num_str != '0':
                    continue
            
            count += 1
        else:
            # Generate all digit combinations for underscores
            def dfs(idx, current_candidate):
                nonlocal count
                if idx == underscore_count:
                    # All underscores filled
                    num_str = ''.join(current_candidate)
                    
                    # Check leading zero
                    if len(num_str) > 1 and num_str[0] == '0':
                        return
                    
                    # Check divisible by 25
                    if len(num_str) >= 2:
                        last_two = num_str[-2:]
                        if last_two not in ('00', '25', '50', '75'):
                            return
                    else:
                        if num_str != '0':
                            return
                    
                    count += 1
                    return
                
                # Try all digits for current underscore
                pos = underscore_pos[idx]
                for digit in '0123456789':
                    current_candidate[pos] = digit
                    dfs(idx + 1, current_candidate)
            
            dfs(0, candidate[:])
    
    print(count)