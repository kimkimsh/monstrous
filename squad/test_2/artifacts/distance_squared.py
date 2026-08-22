"""
Distance‑squared function for the parabola

For any point (x, y) on the graph y = 0.5*x**2 - 9, the squared distance from the origin is:

    D^2(x) = x**2 + (0.5*x**2 - 9)**2

The expanded polynomial is:

    D^2(x) = 0.25*x**4 - 8*x**2 + 81

This module exposes a single function `distance_squared(x)` that returns the value of D^2 for a given x.
"""

def distance_squared(x: float) -> float:
    """Return the squared distance from the origin to the point on the parabola y = 0.5*x**2 - 9.

    Parameters
    ----------
    x : float
        The x‑coordinate of the point on the parabola.

    Returns
    -------
    float
        The value of D^2(x).
    """
    return x**2 + (0.5 * x**2 - 9)**2

# If the module is executed directly, demonstrate a simple example.
if __name__ == "__main__":
    import math
    for val in [-10, -5, 0, 5, 10]:
        print(f"x = {val:>5}  D^2 = {distance_squared(val):.3f}")
