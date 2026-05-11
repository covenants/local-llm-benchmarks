# Detailed Inference Testing Report

**Test Date**: 2026-05-11 11:20:59

## Problem Statement

```
You are an expert Python developer. Solve this step by step:

Problem: Write a Python function that finds the longest substring without repeating characters in a given string. Return both the substring and its length.

Requirements:
1. Handle edge cases (empty string, single character, all repeating)
2. Optimize for O(n) time complexity
3. Include detailed comments explaining the algorithm
4. Add example usage and test cases

Provide the complete, production-ready solution with explanations.
```

## Performance Summary

| Model | Category | Load (s) | Gen (s) | Tokens/s | Quality |
|-------|----------|----------|---------|----------|----------|
| TinyLlama-1.1B | Tier 1: Tiny | 34.59 | 17.30 | 18.67 | 7.0/10 |
| DeepSeek-Coder-1.3B | Tier 2: Small Coding | 29.06 | 25.66 | 18.70 | 6.0/10 |
| Phi-2-2.7B | Tier 2: Small General | 58.88 | 0.55 | 5.47 | 0.0/10 |
| StarCoder2-3B | Tier 2: Small Coding | 314.84 | 33.29 | 15.38 | 8.5/10 |

## Code Quality Metrics

| Model | Function | Comments | Docstring | Examples | Error Handle | Quality |
|-------|----------|----------|-----------|----------|--------------|----------|
| TinyLlama-1.1B | Yes | Yes | No | Yes | No | 7.0/10 |
| DeepSeek-Coder-1.3B | Yes | Yes | Yes | No | No | 6.0/10 |
| Phi-2-2.7B | No | No | No | No | No | 0.0/10 |
| StarCoder2-3B | Yes | Yes | Yes | Yes | No | 8.5/10 |

## Detailed Results by Model

### TinyLlama-1.1B

**Category**: Tier 1: Tiny
**Device**: cuda

#### Performance Metrics

- Load Time: 34.59s
- Generation Time: 17.30s
- Input Tokens: 114
- Output Tokens: 323
- **Throughput: 18.67 tokens/second**
- Total Response Length: 967 characters

#### Code Quality Analysis

- **Quality Score: 7.0/10**
- Has Function Definition: Yes
- Has Comments: Yes
- Has Docstring: No
- Has Examples: Yes
- Has Error Handling: No
- Code Blocks Count: 6

#### Generated Solution Preview

```python
```python
def longest_substring(s):
    # Initialize length of longest substring
    len_longest = 0
    
    # Initialize start and end pointers
    start, end = 0, 0
    
    # Loop through each character
    for I in range(len(s)):
        
        # If the character is not repeating, add it to the length of the longest substring
        if s[i] not in s[start:end].cache:
            len_longest = max(len_longest, i - start + 1)
            start = i + 1
            
    # Return both the substring and its length
    return s[start:end], len_longest
```

Example usage:
```python
>>> longest_substring("abcabbc")
('b', 5)
>>> longest_substring("abbbcc")
('b', 3)
>>> longest_substring("abba")
('b', 2)
>>> longest_substring("abbbb")
('b', 2)
```

Test cases:
```python
assert longest_substring("abcabbc") == ('b', 5)
assert longest_substring("abbbcc") == ('b', 3)
assert longest_substring("abba") == ('b', 2)
assert longest_substring("abbbb") == ('b', 2)
```
```

### DeepSeek-Coder-1.3B

**Category**: Tier 2: Small Coding
**Device**: cuda

#### Performance Metrics

- Load Time: 29.06s
- Generation Time: 25.66s
- Input Tokens: 113
- Output Tokens: 480
- **Throughput: 18.70 tokens/second**
- Total Response Length: 1620 characters

#### Code Quality Analysis

- **Quality Score: 6.0/10**
- Has Function Definition: Yes
- Has Comments: Yes
- Has Docstring: Yes
- Has Examples: No
- Has Error Handling: No
- Code Blocks Count: 2

#### Generated Solution Preview

```python
Solution:

```python
def longest_substring(s):
    """
    This function returns the longest substring without repeating characters.
    """
    # Initialize the maximum length, start index, and end index
    max_length = 0
    start = 0
    end = 0
    # Initialize a set to store the characters
    char_set = set()

    # Loop through the string
    for i in range(len(s)):
        # If the character is in the set, update the start index
        if s[i] in char_set:
            start = i + 1
        else:
            # Else, update the maximum length and end index
            max_length = max(max_length, i - start + 1)
            end = i

        # Add the character to the set
        char_set.add(s[i])

    # Return the longest substring and its length
    return s[start:end+1], max_length

# Test cases
print(longest_substring('abcabcbb'))  # ('abc', 3)
print(longest_substring('bbbbbb'))  # ('b', 1)
print(longest_substring('pwwkew'))  # ('wke', 3)
print(longest_substring(''))  # ('', 0)
print(longest_substring('a'))  # ('a', 1)
print(longest_substring('abcdefgh'))  # ('defgh', 3)
```

This solution uses a sliding window approach. It maintains a set of characters and a pointer to the start of the window. When it encounters a character that's already in the set, it moves the start pointer to the next character. It keeps track of the maximum length seen so far and the end of the window. The time complexity of this solution is O(n) because each character is visited once, and th
```

### Phi-2-2.7B

**Category**: Tier 2: Small General
**Device**: cuda

#### Performance Metrics

- Load Time: 58.88s
- Generation Time: 0.55s
- Input Tokens: 109
- Output Tokens: 3
- **Throughput: 5.47 tokens/second**
- Total Response Length: 0 characters

#### Code Quality Analysis

- **Quality Score: 0.0/10**
- Has Function Definition: No
- Has Comments: No
- Has Docstring: No
- Has Examples: No
- Has Error Handling: No
- Code Blocks Count: 0

#### Generated Solution Preview

```python

```

### StarCoder2-3B

**Category**: Tier 2: Small Coding
**Device**: cuda

#### Performance Metrics

- Load Time: 314.84s
- Generation Time: 33.29s
- Input Tokens: 109
- Output Tokens: 512
- **Throughput: 15.38 tokens/second**
- Total Response Length: 1860 characters

#### Code Quality Analysis

- **Quality Score: 8.5/10**
- Has Function Definition: Yes
- Has Comments: Yes
- Has Docstring: Yes
- Has Examples: Yes
- Has Error Handling: No
- Code Blocks Count: 7

#### Generated Solution Preview

```python
Solution:

The following solution is based on a brute force approach where we iterate through all possible substrings and then check if the substring has no repeating characters.

The time complexity of the solution is O(n^2) because we iterate through all substrings of length 1 to n, and we check each substring for no repeating characters.

The function `find_longest_substring` has the following signature:

```python
def find_longest_substring(s):
```

Example usage:

```python
# Example 1
longest_substring = find_longest_substring("abc")
print(longest_substring) # ("abc", 3)

# Example 2
longest_substring = find_longest_substring("abba")
print(longest_substring) # ("ab", 2)

# Example 3
longest_substring = find_longest_substring("abcabcbb")
print(longest_substring) # ("abc", 3)

# Example 4
longest_substring = find_longest_substring("pwwkew")
print(longest_substring) # ("wke", 3)
```

Test cases:

```python
# Test cases
assert find_longest_substring("abc") == ("abc", 3)
assert find_longest_substring("abba") == ("ab", 2)
assert find_longest_substring("abcabcbb") == ("abc", 3)
assert find_longest_substring("pwwkew") == ("wke", 3)
assert find_longest_substring("") == (None, 0)
```

The following is the complete Python code for the solution:

```python
def find_longest_substring(s):
    """
    Finds the longest substring without repeating characters in a given string.
    Returns both the substring and its length.
```


## Performance Rankings

### Fastest Models (Tokens/Second)

1. **DeepSeek-Coder-1.3B**: 18.70 tokens/sec
2. **TinyLlama-1.1B**: 18.67 tokens/sec
3. **StarCoder2-3B**: 15.38 tokens/sec
4. **Phi-2-2.7B**: 5.47 tokens/sec

### Best Code Quality

1. **StarCoder2-3B**: 8.5/10
2. **TinyLlama-1.1B**: 7.0/10
3. **DeepSeek-Coder-1.3B**: 6.0/10
4. **Phi-2-2.7B**: 0.0/10

## Recommendations

**Fastest Model**: DeepSeek-Coder-1.3B (18.70 tokens/sec)
- Best for: Real-time applications, speed-critical systems
- Use when: Response time is more important than quality

**Best Code Quality**: StarCoder2-3B (8.5/10)
- Best for: Production code generation, complex problems
- Use when: Code quality is critical

**Best Overall Balance**: StarCoder2-3B
- Best for: General-purpose use, good balance of speed and quality

