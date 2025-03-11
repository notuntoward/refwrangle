import sys
import pathlib as pl
import time
# Define paths and credentials
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw  

# Example Usage:
if __name__ == '__main__':
    # Create a Timer object
    timer = rfw.Timer()

    # Simulate some work
    time.sleep(1)

    # Mark the time and print the elapsed time
    elapsed = timer.mark()
    print(f"Returned elapsed time: {elapsed:.4f} seconds")

    # Simulate more work
    time.sleep(0.5)

    # Mark the time but don't print it
    elapsed = timer.mark(print_elapsed=False)
    print(f"Returned elapsed time (without printing): {elapsed:.4f} seconds")
