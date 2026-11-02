import sys
from collections import deque

def next_bit(bits):
    if not bits:
        raise IndexError("No more bits available.")
    bit = bits.popleft()
    if bit == '0':
        return 0
    if bit == '1':
        return 1
    raise ValueError("Invalid bit value: {}".format(bit))

def nand(bits):
    return 1 if not (cond(bits) and cond(bits)) else 0

def cond(bits):
    return nand(bits) if next_bit(bits) else next_bit(bits)

def interpret(bits):
    try:
        while bits:
            bit = str(cond(bits))
            print(bit, end="")
            bits.append(bit)
    except (IndexError, ValueError) as e:
        print()

if __name__ == "__main__":
    bits = deque(sys.stdin.read().strip())
    interpret(bits)
