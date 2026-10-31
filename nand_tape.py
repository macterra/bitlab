"""Total binary syntax for a NAND tape machine. See NAND_TAPE.md."""

import argparse
import json
import sys
from dataclasses import dataclass, field


def decode(bits):
    """Every finite binary string decodes; absent operand bits are zero."""
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

    def number():
        value = 0
        while bit():
            value += 1
        return value

    instructions = []
    while pos < len(bits):
        if bit() == 0:
            instructions.append(("nand", bit()))
        elif bit() == 0:
            instructions.append(("move", 1 if bit() else -1))
        else:
            instructions.append(("branch", number(), number()))
    return instructions


def encode(instructions):
    """Canonical complete encoding; source programs can also be truncated."""
    pieces = []
    for op, *args in instructions:
        if op == "nand" and len(args) == 1 and args[0] in (0, 1):
            pieces.append("0" + str(args[0]))
            continue
        elif op == "move" and len(args) == 1 and args[0] in (-1, 1):
            pieces.append("101" if args[0] == 1 else "100")
            continue
        elif op == "branch" and len(args) == 2 and min(args) >= 0:
            prefix, numbers = "11", args
        else:
            raise ValueError(f"invalid assembly instruction: {(op, *args)}")
        pieces.append(prefix)
        pieces.extend("1" * n + "0" for n in numbers)
    return "".join(pieces)


@dataclass
class Machine:
    program: list
    ones: set = field(default_factory=set)
    head: int = 0
    pc: int = 0
    steps: int = 0

    @property
    def halted(self):
        return not 0 <= self.pc < len(self.program)

    def step(self):
        """Execute one instruction. Return False only if already halted."""
        if self.halted:
            return False
        op, *args = self.program[self.pc]
        self.pc += 1
        if op == "nand":
            # Both sources are read before the destination is written.
            if self.head in self.ones and self.head + args[0] in self.ones:
                self.ones.discard(self.head)
            else:
                self.ones.add(self.head)
        elif op == "move":
            self.head += args[0]
        elif op == "branch":
            self.pc = args[int(self.head in self.ones)]
        else:
            raise ValueError(f"unknown assembly operation: {op}")
        self.steps += 1
        return True

    def run(self, budget):
        """Host-side execution budget; exhaustion is suspension, not halting."""
        if budget < 0:
            raise ValueError("budget must be nonnegative")
        for _ in range(budget):
            if not self.step():
                break
        return "halted" if self.halted else "suspended"


def compile_tm(transitions, start):
    """Compile a binary Turing machine to bits.

    (state, read_bit) -> (write_bit, movement, next_state).
    Movement is -1, 0, or 1; None as next_state means halt after writing/moving.
    Missing transitions halt without changing the tape or head.
    Source cell i lives at target cell 2*i; odd target cells must start at zero.
    """
    states = [start]
    for (state, read), (write, movement, next_state) in transitions.items():
        if state is None or read not in (0, 1) or write not in (0, 1):
            raise ValueError("states must be non-None and symbols must be bits")
        if movement not in (-1, 0, 1):
            raise ValueError("movement must be -1, 0, or 1")
        for candidate in (state, next_state):
            if candidate is not None and candidate not in states:
                states.append(candidate)
    if start is None:
        raise ValueError("start state must be non-None")

    code, labels = [], {}
    for state in states:
        labels[("state", state)] = len(code)
        code.append(("branch", ("edge", state, 0), ("edge", state, 1)))
        for read in (0, 1):
            transition = transitions.get((state, read))
            if transition is None:
                continue
            labels[("edge", state, read)] = len(code)
            write, movement, next_state = transition
            # The adjacent odd cell is permanently zero: NAND(x, 0) = 1.
            code.append(("nand", 1))
            if write == 0:
                code.append(("nand", 0))
            if movement:
                code.extend([("move", movement), ("move", movement)])
            target = ("state", next_state)
            code.append(("branch", target, target))

    resolved = []
    for op, *args in code:
        if op == "branch":
            args = [labels.get(label, len(code)) for label in args]
        resolved.append((op, *args))
    return encode(resolved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", nargs="?", help="bitstring; default: stdin")
    parser.add_argument("--input", default="", help="initial tape bits at cells 0,1,...")
    parser.add_argument("--steps", type=int, default=10000, help="execution budget")
    parser.add_argument("--decode", action="store_true", help="show decoded instructions")
    args = parser.parse_args()
    bits = args.program if args.program is not None else sys.stdin.read()
    try:
        program = decode("".join(bits.split()))
        if any(bit not in "01" for bit in args.input):
            raise ValueError("input must contain only 0 and 1")
        machine = Machine(program, {i for i, bit in enumerate(args.input) if bit == "1"})
        status = machine.run(args.steps)
    except ValueError as error:
        parser.error(str(error))
    result = dict(status=status, steps=machine.steps, pc=machine.pc,
                  head=machine.head, ones=sorted(machine.ones))
    if args.decode:
        result["program"] = program
    print(json.dumps(result))


if __name__ == "__main__":
    main()
