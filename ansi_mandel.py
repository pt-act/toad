import os
import sys


def mandelbrot(c: complex, max_iter: int) -> int:
    """Determine the number of iterations for a point in the Mandelbrot set.

    Args:
        c (complex): The complex point to test.
        max_iter (int): The maximum number of iterations to test.

    Returns:
        int: Number of iterations before escape or max_iter.
    """
    z = 0 + 0j
    for n in range(max_iter):
        if abs(z) > 2:
            return n
        z = z * z + c
    return max_iter

def colorize(iter_count: int, max_iter: int) -> str:
    """Get an ANSI color code based on the iteration count.

    Args:
        iter_count (int): Number of iterations completed before escape.
        max_iter (int): Maximum number of iterations allowed.

    Returns:
        str: ANSI escape code for color.
    """
    if iter_count == max_iter:
        return "\033[48;5;0m"  # Black background for points in the set
    else:
        # Create a gradient from 17 to 231 (blue to red) for escaping points
        color_code = 17 + int((iter_count / max_iter) * 214)
        return f"\033[48;5;{color_code}m"

def draw_mandelbrot(width: int, height: int, max_iter: int) -> None:
    """Draw the Mandelbrot set in the terminal using ANSI colors.

    Args:
        width (int): Width of the output in terminal characters.
        height (int): Height of the output in terminal rows.
        max_iter (int): Maximum number of iterations for Mandelbrot calculation.
    """
    # Clear screen and hide cursor
    print("\033[2J\033[H\033[?25l", end="")
    
    for y in range(height):
        # Move cursor to start of line
        print(f"\033[{y+1};1H", end="")
        
        for x in range(width):
            # Map the (x, y) pixel to a point in the complex plane
            real = (x / width) * 3.5 - 2.5
            imag = (y / height) * 2.0 - 1.0
            c = complex(real, imag)

            # Calculate the number of iterations
            iter_count = mandelbrot(c, max_iter)

            # Get the color for this point and print a space (box)
            color = colorize(iter_count, max_iter)
            print(f"{color}  ", end="")

        # Reset color at end of line
        print("\033[0m", end="")
    
    # Show cursor again and ensure we're at the bottom
    print("\033[?25h", end="")
    sys.stdout.flush()

# Get terminal dimensions
try:
    terminal_size = os.get_terminal_size()
    width = terminal_size.columns // 2  # Divide by 2 since we print 2 spaces per pixel
    height = terminal_size.lines - 1  # Leave one line for prompt
except OSError:
    # Fallback if terminal size cannot be determined
    width = 80
    height = 40

max_iter = 100  # Maximum iterations for Mandelbrot calculation

# Draw the Mandelbrot set
draw_mandelbrot(width, height, max_iter)