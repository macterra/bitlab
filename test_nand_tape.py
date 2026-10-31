import itertools
import random
import unittest

from nand_tape import Machine, compile_tm, decode, encode


class NandTapeTests(unittest.TestCase):
    def test_short_programs_are_total(self):
        # Every bitstring through length 12: 8,191 programs, including empty.
        for length in range(13):
            for digits in itertools.product("01", repeat=length):
                bits = "".join(digits)
                program = decode(bits)
                self.assertEqual(decode(encode(program)), program)
                machine = Machine(program)
                self.assertIn(machine.run(30), ("halted", "suspended"))

    def test_end_of_file_rules(self):
        self.assertEqual(decode(""), [])
        self.assertEqual(decode("0"), [("nand", 0)])
        self.assertEqual(decode("1"), [("move", -1)])
        self.assertEqual(decode("11"), [("branch", 0, 0)])
        self.assertEqual(decode("1111"), [("branch", 2, 0)])
        self.assertEqual(Machine(decode("")).run(0), "halted")
        self.assertEqual(Machine(decode("11")).run(100), "suspended")
        self.assertEqual(Machine(decode("111010")).run(1), "halted")

    def test_nand_truth_table_and_aliasing(self):
        for a, b in itertools.product((0, 1), repeat=2):
            ones = {position for position, bit in ((0, a), (1, b)) if bit}
            machine = Machine([("nand", 1)], ones)
            machine.step()
            self.assertEqual(int(0 in machine.ones), 1 - a * b)
        machine = Machine(decode("0000"))  # Two flips of the same cell.
        machine.run(2)
        self.assertEqual(machine.ones, set())

    def test_growth_and_resume(self):
        code = decode(encode([("nand", 1), ("move", 1), ("branch", 0, 0)]))
        machine = Machine(code)
        self.assertEqual(machine.run(300), "suspended")
        self.assertEqual(machine.head, 100)
        self.assertEqual(machine.ones, set(range(100)))
        machine.run(300)
        self.assertEqual(machine.ones, set(range(200)))

    def test_tm_unary_increment(self):
        bits = compile_tm({("scan", 1): (1, 1, "scan"),
                           ("scan", 0): (1, 0, None)}, "scan")
        for n in range(20):
            machine = Machine(decode(bits), {2 * i for i in range(n)})
            self.assertEqual(machine.run(1000), "halted")
            self.assertEqual(machine.ones, {2 * i for i in range(n + 1)})
            self.assertEqual(machine.head, 2 * n)

    def test_compiler_against_independent_tm(self):
        rng = random.Random(42)
        for _ in range(300):
            transitions = {}
            for state in range(3):
                for bit in (0, 1):
                    if rng.random() < 0.85:
                        transitions[state, bit] = (
                            rng.randrange(2), rng.choice((-1, 0, 1)),
                            rng.choice((0, 1, 2, None)))
            tape = {i for i in range(-3, 4) if rng.randrange(2)}
            machine = Machine(decode(compile_tm(transitions, 0)), {2 * i for i in tape})
            state, head, cost, halted = 0, 0, 0, False
            for _ in range(40):
                rule = transitions.get((state, int(head in tape)))
                if rule is None:
                    cost += 1  # Dispatch jumps straight to halt.
                    halted = True
                    break
                write, movement, state = rule
                if write:
                    tape.add(head)
                else:
                    tape.discard(head)
                head += movement
                cost += 3 + (write == 0) + 2 * abs(movement)
                if state is None:
                    halted = True
                    break
            machine.run(cost)
            self.assertEqual(machine.halted, halted)
            self.assertEqual(machine.head, 2 * head)
            self.assertEqual(machine.ones, {2 * i for i in tape})


if __name__ == "__main__":
    unittest.main()
