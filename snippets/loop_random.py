import time
import random
import sys

i = 0
try:
    while True:
        i = random.randint(1, 100)
        print(f"~[{i}]")
        sys.stdout.flush()
        time.sleep(2)
except KeyboardInterrupt:
    pass
