"""Build, measure, and run the compact-address NAND tape self-interpreter."""

import argparse
import json
from pathlib import Path

from languages.compact_tape import decode, encode
from languages.nand_tape import Machine
import experiments.self_host as self_host


WIDTH = self_host.COMPACT_WIDTH


def build():
    return self_host.build(binary=True)


def frame(bits, ones=()):
    return self_host.frame(bits, ones, width=WIDTH)


def result(tape):
    return self_host.result(tape, width=WIDTH)


def metrics(code):
    return self_host.metrics(code, encode, ("languages/nand_tape.py", "languages/compact_tape.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", type=Path, help="write compact-dialect program bits")
    parser.add_argument("--report", type=Path, help="write reproducible size report")
    parser.add_argument("--run", help="raw compact-dialect guest source")
    parser.add_argument("--ones", type=int, nargs="*", default=[])
    parser.add_argument("--steps", type=int, default=1000000)
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
