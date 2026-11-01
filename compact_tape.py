"""NAND tape with self-delimiting binary branch addresses (a separate dialect)."""

import argparse
import json
import sys

from nand_tape import Machine


def number(n):
    """MSB-first pairs 1b, followed by 0. Zero has the canonical encoding 0."""
    if n < 0:
        raise ValueError("branch addresses must be nonnegative")
    return "".join("1" + bit for bit in bin(n)[2:]) + "0" if n else "0"


def encode(instructions):
    pieces = []
    for op, *args in instructions:
        if op == "nand" and len(args) == 1 and args[0] in (0, 1):
            pieces.append("0" + str(args[0]))
        elif op == "move" and len(args) == 1 and args[0] in (-1, 1):
            pieces.append("101" if args[0] == 1 else "100")
        elif op == "branch" and len(args) == 2:
            pieces.append("11" + number(args[0]) + number(args[1]))
        else:
            raise ValueError(f"invalid assembly instruction: {(op, *args)}")
    return "".join(pieces)


def decode(bits):
    """Total on finite bitstrings, including noncanonical and truncated numbers."""
    if any(bit not in "01" for bit in bits):
        raise ValueError("program must contain only 0 and 1")
    pos = 0

    def bit():
        nonlocal pos
        if pos == len(bits):
            return 0
        value = int(bits[pos])
        pos += 1
        return value

    def address():
        value = 0
        while bit():
            value = 2 * value + bit()
        return value

    instructions = []
    while pos < len(bits):
        if bit() == 0:
            instructions.append(("nand", bit()))
        elif bit() == 0:
            instructions.append(("move", 1 if bit() else -1))
        else:
            instructions.append(("branch", address(), address()))
    return instructions


def offsets(bits):
    """Physical start offsets, including noncanonical operand encodings.

    This inspection utility is not used by the self-interpreter or input framer.
    """
    starts, pos = [], 0

    def take():
        nonlocal pos
        if pos == len(bits):
            return "0"
        value = bits[pos]
        pos += 1
        return value

    if any(bit not in "01" for bit in bits):
        raise ValueError("program must contain only 0 and 1")
    while pos < len(bits):
        starts.append(pos)
        if take() == "0" or take() == "0":
            take()
        else:
            for _ in range(2):
                while take() == "1":
                    take()
    return starts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", nargs="?", help="bitstring; default stdin")
    parser.add_argument("--ones", nargs="*", type=int, default=[])
    parser.add_argument("--steps", type=int, default=10000)
    args = parser.parse_args()
    bits = args.program if args.program is not None else sys.stdin.read()
    try:
        machine = Machine(decode("".join(bits.split())), set(args.ones))
        status = machine.run(args.steps)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(dict(status=status, steps=machine.steps, pc=machine.pc,
                          head=machine.head, ones=sorted(machine.ones))))


if __name__ == "__main__":
    main()
