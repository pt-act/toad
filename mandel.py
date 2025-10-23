def mandelbrot(c, max_iter=100):
    z = 0
    for n in range(max_iter):
        if abs(z) > 2:
            return n
        z = z*z + c
    return max_iter

def generate_mandelbrot(width=80, height=40, x_min=-2.5, x_max=1.5, y_min=-2.0, y_max=2.0):
    chars = " .:-=+*#%@"
    
    for y in range(height):
        line = ""
        for x in range(width):
            # Map pixel coordinates to complex plane
            real = x_min + (x / width) * (x_max - x_min)
            imag = y_min + (y / height) * (y_max - y_min)
            c = complex(real, imag)
            
            # Calculate mandelbrot value
            m = mandelbrot(c)
            
            # Map to character
            char_index = min(int(m / 10), len(chars) - 1)
            line += chars[char_index]
        
        print(line)

if __name__ == "__main__":
    print("Mandelbrot Set")
    print("=" * 80)
    generate_mandelbrot()