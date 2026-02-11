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
        for digits_tuple in product('0123456789', repeat=underscore_count):
            # Fill underscores
            for pos, digit in zip(underscore_pos, digits_tuple):
                candidate[pos] = digit
            
            # Build final string
            num_str = ''.join(candidate)
            
            # Check leading zero
            if len(num_str) > 1 and num_str[0] == '0':
                continue
            
            # Check divisible by 25 (last two digits must be 00, 25, 50, 75)
            if len(num_str) >= 2:
                last_two = num_str[-2:]
                if last_two not in ('00', '25', '50', '75'):
                    continue
            else:
                # Single digit case: must be 0 to be divisible by 25
                if num_str != '0':
                    continue
            
            count += 1
    
    print(count)