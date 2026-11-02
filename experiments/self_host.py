"""Assemble a NAND-tape self-interpreter. Python generates code, never guest steps.

The emitted program reads framed raw bits and interprets them using only the
three ordinary NAND-tape instructions. See SELF_INTERPRETER.md for the ABI.
"""

from core.artifacts import ROOT, repo_path

import argparse
import hashlib
import json
from pathlib import Path

from languages.nand_tape import Machine, decode, encode


# Each row has nine bits, each followed by a permanently zero scratch cell.
ORIGIN, SOURCE, PRESENT, READER, POS_HEAD, NEG_HEAD, POS_DATA, NEG_DATA, COUNT = range(0, 18, 2)
WIDTH = 18
COUNTER_END = 18
COMPACT_WIDTH = 20


class Assembler:
    def __init__(self, optimize=True, width=WIDTH):
        self.code = []
        self.labels = {}
        self.serial = 0
        self.known = None
        self.optimize = optimize
        self.width = width

    def fresh(self):
        self.serial += 1
        return f"internal_{self.serial}"

    def label(self, name):
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = len(self.code)
        self.known = None

    def move(self, distance):
        self.code.extend([("move", 1 if distance > 0 else -1)] * abs(distance))
        if distance:
            self.known = None

    def one(self):
        self.code.append(("nand", 1))  # Every used lane has a zero right neighbor.
        self.known = 1

    def zero(self):
        self.one()
        self.flip()

    def flip(self):
        self.code.append(("nand", 0))
        if self.known is not None:
            self.known = 1 - self.known

    def branch(self, zero, one):
        if self.optimize and zero == one and self.known is not None:
            # An unconditional jump's unreachable arm can use address zero.
            # This changes no instruction indices and saves unary operand bits.
            if self.known:
                zero = 0
            else:
                one = 0
        self.code.append(("branch", zero, one))
        self.known = None

    def jump(self, target):
        self.branch(target, target)

    def home(self, lane):
        """From a known lane in a nonnegative row, return to origin lane 0."""
        self.move(-lane)
        loop, left, done = self.fresh(), self.fresh(), self.fresh()
        self.label(loop)
        self.branch(left, done)
        self.label(left)
        self.move(-self.width)
        self.jump(loop)
        self.label(done)
        self.known = 1  # The loop exits exactly when ORIGIN is one.

    def seek(self, lane, value=1):
        """From home, scan right for a lane bit of the requested value."""
        self.move(lane)
        loop, right, done = self.fresh(), self.fresh(), self.fresh()
        self.label(loop)
        self.branch(right if value else done, done if value else right)
        self.label(right)
        self.move(self.width)
        self.jump(loop)
        self.label(done)
        self.known = value

    def head(self, positive, negative):
        """From home, find either guest-head marker; leave the head on it."""
        self.move(POS_HEAD)
        loop, check_negative, right = self.fresh(), self.fresh(), self.fresh()
        self.label(loop)
        self.branch(check_negative, positive)
        self.label(check_negative)
        self.move(NEG_HEAD - POS_HEAD)
        self.branch(right, negative)
        self.label(right)
        self.move(self.width + POS_HEAD - NEG_HEAD)
        self.jump(loop)

    def fetch(self, zero, one):
        """Read a raw source bit; EOF yields zero without moving READER.

        Entry and both continuations are at home. Return values are represented
        by control flow, not by Python execution or a host-side guest register.
        """
        eof, present, bit_zero, bit_one = [self.fresh() for _ in range(4)]
        self.seek(READER)
        self.move(PRESENT - READER)
        self.branch(eof, present)
        self.label(eof)
        self.home(PRESENT)
        self.jump(zero)
        self.label(present)
        if zero == one:
            # A discarded operand needs no value dispatch or duplicate path.
            self.move(READER - PRESENT)
            self.zero()
            self.move(self.width)
            self.one()
            self.home(READER)
            self.jump(zero)
            return
        self.move(SOURCE - PRESENT)
        self.branch(bit_zero, bit_one)
        for label, target in ((bit_zero, zero), (bit_one, one)):
            self.label(label)
            self.move(READER - SOURCE)
            self.zero()
            self.move(self.width)
            self.one()
            self.home(READER)
            self.jump(target)

    def available(self, yes, no):
        """Test whether another physical source bit exists, without consuming it."""
        missing, present = self.fresh(), self.fresh()
        self.seek(READER)
        self.move(PRESENT - READER)
        self.branch(missing, present)
        for label, target in ((missing, no), (present, yes)):
            self.label(label)
            self.home(PRESENT)
            self.jump(target)

    def finish(self):
        return [(op, *(self.labels[arg] if isinstance(arg, str) else arg for arg in args)) if op == "branch"
                else (op, *args) for op, *args in self.code]


def build(optimize=True, binary=False):
    """Return the actual self-interpreter's instruction list and debug labels."""
    width = COMPACT_WIDTH if binary else WIDTH
    a = Assembler(optimize=optimize, width=width)
    # Initialize metadata in the program itself; the input frame contains none.
    a.one()
    a.move(READER)
    a.one()
    a.move(POS_HEAD - READER)
    a.one()
    if binary:
        a.move(COUNTER_END - POS_HEAD)
        a.one()
        a.home(COUNTER_END)
    else:
        a.home(POS_HEAD)

    a.label("step")
    a.available("opcode", "halt")
    a.label("opcode")
    a.fetch("nand_operand", "opcode_second")
    a.label("opcode_second")
    a.fetch("move_operand", "branch_head")
    a.label("nand_operand")
    a.fetch("not_head", "nand_head")
    a.label("move_operand")
    a.fetch("left_head", "right_head")

    a.label("not_head")
    a.head("not_positive", "not_negative")
    for name, marker, data in (("not_positive", POS_HEAD, POS_DATA),
                               ("not_negative", NEG_HEAD, NEG_DATA)):
        a.label(name)
        a.move(data - marker)
        a.flip()
        a.home(data)
        a.jump("step")

    a.label("nand_head")
    a.head("nand_positive", "nand_negative")
    for name, marker, data in (("positive", POS_HEAD, POS_DATA),
                               ("negative", NEG_HEAD, NEG_DATA)):
        a.label("nand_" + name)
        a.move(data - marker)
        a.branch("nand_set_" + name, "nand_neighbor_" + name)
        a.label("nand_set_" + name)
        a.one()
        a.home(data)
        a.jump("step")

    a.label("nand_neighbor_positive")
    a.move(width)
    a.branch("nand_keep_positive", "nand_clear_positive")
    a.label("nand_clear_positive")
    a.move(-width)
    a.zero()
    a.home(POS_DATA)
    a.jump("step")
    a.label("nand_keep_positive")
    a.home(POS_DATA)
    a.jump("step")

    a.label("nand_neighbor_negative")
    a.move(-NEG_DATA)
    a.branch("nand_negative_inner", "nand_negative_boundary")
    # Negative cell -k-1 has right neighbor -k, except -1 whose neighbor is 0.
    for label, displacement, lane in (
        ("nand_negative_inner", -width + NEG_DATA, NEG_DATA),
        ("nand_negative_boundary", POS_DATA, POS_DATA),
    ):
        clear, keep = a.fresh(), a.fresh()
        a.label(label)
        a.move(displacement)
        a.branch(keep, clear)
        a.label(clear)
        a.move(NEG_DATA - displacement)
        a.zero()
        a.home(NEG_DATA)
        a.jump("step")
        a.label(keep)
        a.home(lane)
        a.jump("step")

    for direction in ("left", "right"):
        a.label(direction + "_head")
        a.head(direction + "_positive", direction + "_negative")
        for sign, marker, other in (("positive", POS_HEAD, NEG_HEAD),
                                    ("negative", NEG_HEAD, POS_HEAD)):
            a.label(direction + "_" + sign)
            outward = (direction == "right") == (sign == "positive")
            if outward:
                a.zero()
                a.move(width)
                a.one()
                a.home(marker)
                a.jump("step")
            else:
                inner, boundary = a.fresh(), a.fresh()
                a.move(-marker)
                a.branch(inner, boundary)
                a.label(inner)
                a.move(marker)
                a.zero()
                a.move(-width)
                a.one()
                a.home(marker)
                a.jump("step")
                a.label(boundary)
                a.move(marker)
                a.zero()
                a.move(other - marker)
                a.one()
                a.home(other)
                a.jump("step")

    a.label("branch_head")
    a.head("branch_positive", "branch_negative")
    for sign, marker, data in (("positive", POS_HEAD, POS_DATA),
                               ("negative", NEG_HEAD, NEG_DATA)):
        z, o = a.fresh(), a.fresh()
        a.label("branch_" + sign)
        a.move(data - marker)
        a.branch(z, o)
        for label, target in ((z, "count_operand"), (o, "skip_first_operand")):
            a.label(label)
            a.home(data)
            a.jump(target)

    def skip_number(label, done):
        a.label(label)
        if binary:
            a.fetch(done, label + "_digit")
            a.label(label + "_digit")
            a.fetch(label, label)
        else:
            a.fetch(done, label)

    skip_number("skip_first_operand", "count_operand")
    a.label("count_operand")
    if binary:
        a.fetch("reset_reader", "count_digit")
        a.label("count_digit")
        a.fetch("append_zero", "append_one")
        for label, value in (("append_zero", 0), ("append_one", 1)):
            a.label(label)
            a.seek(COUNTER_END)
            if value:
                a.move(COUNT - COUNTER_END)
                a.one()
                a.move(COUNTER_END - COUNT)
            a.zero()
            a.move(width)
            a.one()
            a.home(COUNTER_END)
            a.jump("count_operand")
    else:
        a.fetch("reset_reader", "increment_count")
        a.label("increment_count")
        a.seek(COUNT, value=0)
        a.one()
        a.home(COUNT)
        a.jump("count_operand")
    a.label("reset_reader")
    a.seek(READER)
    a.zero()
    a.home(READER)
    a.move(READER)
    a.one()
    a.move(-READER)

    a.label("seek_instruction")
    a.move(COUNT)
    if binary:
        a.label("counter_scan")
        a.branch("counter_check_end", "count_nonzero")
        a.label("counter_check_end")
        a.move(COUNTER_END - COUNT)
        a.branch("counter_scan_next", "count_done")
        a.label("counter_scan_next")
        a.move(width + COUNT - COUNTER_END)
        a.jump("counter_scan")
        a.label("count_done")
        a.zero()  # Remove end marker; all digit bits are already zero.
        a.home(COUNTER_END)
        a.move(COUNTER_END)
        a.one()  # Empty binary counter at the next instruction boundary.
        a.move(-COUNTER_END)
        a.jump("step")
        a.label("count_nonzero")
        a.home(COUNT)
        a.seek(COUNTER_END)
        a.move(-width + COUNT - COUNTER_END)
        a.label("decrement_digit")
        a.branch("borrow", "decrement_done")
        a.label("borrow")
        a.one()
        a.move(-width)
        a.jump("decrement_digit")
        a.label("decrement_done")
        a.zero()
        a.home(COUNT)
    else:
        a.branch("count_done", "count_nonzero")
        a.label("count_done")
        a.move(-COUNT)
        a.jump("step")
        a.label("count_nonzero")
        a.move(-COUNT)
        a.seek(COUNT, value=0)
        a.move(-width)
        a.zero()
        a.home(COUNT)
    a.available("skip_opcode", "halt")
    a.label("skip_opcode")
    a.fetch("skip_fixed_operand", "skip_opcode_second")
    a.label("skip_opcode_second")
    a.fetch("skip_fixed_operand", "skip_unary_zero")
    a.label("skip_fixed_operand")
    a.fetch("seek_instruction", "seek_instruction")
    skip_number("skip_unary_zero", "skip_unary_one")
    skip_number("skip_unary_one", "seek_instruction")
    a.label("halt")  # Exactly one past the final instruction.
    return a.finish(), a.labels


def frame(bits, ones=(), width=WIDTH):
    """Encode raw program bits and finite guest tape data, without parsing code."""
    if any(bit not in "01" for bit in bits):
        raise ValueError("program must contain only 0 and 1")
    tape = set()
    for i, bit in enumerate(bits):
        tape.add(width * i + PRESENT)
        if bit == "1":
            tape.add(width * i + SOURCE)
    for i in ones:
        tape.add(width * (i if i >= 0 else -i - 1) +
                 (POS_DATA if i >= 0 else NEG_DATA))
    return tape


def result(tape, width=WIDTH):
    """Read the guest's output tape/head; ignore interpreter working storage."""
    ones, heads = set(), []
    for position in tape:
        row, lane = divmod(position, width)
        if lane == POS_DATA:
            ones.add(row)
        elif lane == NEG_DATA:
            ones.add(-row - 1)
        elif lane == POS_HEAD:
            heads.append(row)
        elif lane == NEG_HEAD:
            heads.append(-row - 1)
    if len(heads) != 1:
        raise ValueError("guest head is not at an instruction boundary")
    return ones, heads[0]


def metrics(code, encoder=encode, reference_files=("languages/nand_tape.py",)):
    bits = encoder(code)
    by_operation = {op: sum(len(encoder([instruction])) for instruction in code
                            if instruction[0] == op)
                    for op in ("nand", "move", "branch")}
    reference = b"".join(repo_path(name).read_bytes() for name in reference_files)
    return dict(bits=len(bits), packed_bytes=(len(bits) + 7) // 8,
                instructions=len(code), bits_by_operation=by_operation,
                sha256=hashlib.sha256(bits.encode("ascii")).hexdigest(),
                reference_python_bytes=len(reference),
                reference_python_sha256=hashlib.sha256(reference).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", type=Path, help="write executable ASCII bitstring")
    parser.add_argument("--report", type=Path, help="write reproducible size report")
    parser.add_argument("--run", help="interpret this raw guest program")
    parser.add_argument("--ones", type=int, nargs="*", default=[], help="guest cells initially 1")
    parser.add_argument("--steps", type=int, default=1000000, help="host instruction budget")
    args = parser.parse_args()
    code, _ = build()
    bits = encode(code)
    report = metrics(code)
    if args.emit:
        args.emit.write_text(bits, encoding="ascii")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.run is not None:
        machine = Machine(decode(bits), frame(args.run, args.ones))
        status = machine.run(args.steps)
        report.update(status=status, host_steps=machine.steps)
        if status == "halted":
            ones, head = result(machine.ones)
            report.update(guest_ones=sorted(ones), guest_head=head)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
