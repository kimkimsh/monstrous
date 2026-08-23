#!/usr/bin/env python3
"""solution.py

This script reads a string from standard input, extracts its first character, concatenates it with the string "UPC", and prints the result.

Usage:
    echo "hello" | python3 solution.py

Output:
    hUPC

The script is self‑contained and can be executed directly.
"""

import sys

def main() -> None:
    # Read the entire input from stdin and strip trailing newlines
    data = sys.stdin.read().rstrip("\n")
    if not data:
        first_char = ""
    else:
        first_char = data[0]
    result = f"{first_char}UPC"
    print(result)

if __name__ == "__main__":
    main()
