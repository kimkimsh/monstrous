#!/usr/bin/env python3
"""Solution for the multiplication table sum problem.

The program reads an integer X from standard input, then computes the sum of all
81 integers in the 9x9 multiplication table (1×1 up to 9×9).  Every entry that
equals X is omitted from the sum.  The result is printed to standard output.

The algorithm is O(81) = O(1) and uses only a few integer variables.
"""

import sys


def main() -> None:
    """Read X, compute the sum excluding X, and print the result."""
    data = sys.stdin.read().strip().split()
    if not data:
        return
    try:
        x = int(data[0])
    except ValueError:
        # If the input is not an integer, we simply exit.
        return

    total = 0
    for i in range(1, 10):
        for j in range(1, 10):
            val = i * j
            if val != x:
                total += val
    print(total)


if __name__ == "__main__":
    main()
