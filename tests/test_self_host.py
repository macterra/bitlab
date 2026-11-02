from core.artifacts import ROOT, repo_path
import itertools
import json
import random
import unittest
from pathlib import Path

from languages.nand_tape import Machine, decode, encode
from experiments.self_host import COUNT, NEG_HEAD, ORIGIN, POS_HEAD, PRESENT, READER, SOURCE, WIDTH, build, frame, metrics, result


class SelfInterpreterTests(unittest.TestCase):
    encoder = staticmethod(encode)
    decoder = staticmethod(decode)
    builder = staticmethod(build)
    framer = staticmethod(frame)
    extract = staticmethod(result)
    measure = staticmethod(metrics)
    width = WIDTH
    artifact_name = "self_host"
    expected_frame = {4, 22, 20, 12, 14}

    @classmethod
    def setUpClass(cls):
        code, cls.labels = cls.builder()
        cls.bits = cls.encoder(code)
        # Execute the binary artifact, not the assembler's unresolved objects.
        cls.code = cls.decoder(cls.bits)
        assert cls.code == code

    def source_offsets(self, bits):
        offsets, cursor = [], 0
        for instruction in self.decoder(bits):
            offsets.append(cursor)
            cursor = min(len(bits), cursor + len(self.encoder([instruction])))
        return offsets

    def boundary(self, machine, budget=2000000):
        for _ in range(budget):
            machine.step()
            if machine.halted or machine.pc == self.labels["step"]:
                return
        self.fail("host budget exhausted before a guest instruction boundary")

    def check_program(self, bits, ones=(), limit=12):
        reference = Machine(self.decoder(bits), set(ones))
        offsets = self.source_offsets(bits)
        initial = self.framer(bits, ones)
        hosted = Machine(self.code, initial.copy())
        self.boundary(hosted)  # Initialization performed by NAND tape itself.
        for _ in range(limit):
            if reference.halted:
                self.boundary(hosted)  # EOF check, not another guest instruction.
                self.assertTrue(hosted.halted, bits)
                break
            reference.step()
            self.boundary(hosted)
            self.assertEqual(self.extract(hosted.ones), (reference.ones, reference.head), bits)
            if hosted.halted:
                self.assertTrue(reference.halted, bits)
                break
            if not reference.halted:
                self.assertIn(self.width * offsets[reference.pc] + READER, hosted.ones, bits)
            self.assertFalse(any(p % self.width == COUNT for p in hosted.ones))
        else:
            if reference.halted:
                self.boundary(hosted)
                self.assertTrue(hosted.halted, bits)
            else:
                self.assertFalse(hosted.halted, bits)
        self.assertEqual(self.extract(hosted.ones), (reference.ones, reference.head), bits)
        # The interpreter must preserve raw program data and all scratch zeros.
        for lane in (SOURCE, PRESENT):
            self.assertEqual({p for p in hosted.ones if p % self.width == lane},
                             {p for p in initial if p % self.width == lane})
        self.assertTrue(all(p >= 0 and p % 2 == 0 for p in hosted.ones))
        self.assertEqual({p for p in hosted.ones if p % self.width == ORIGIN}, {ORIGIN})
        self.assertEqual(sum(p % self.width == READER for p in hosted.ones), 1)
        self.assertEqual(sum(p % self.width in (POS_HEAD, NEG_HEAD) for p in hosted.ones), 1)
        return reference, hosted

    def test_every_program_through_eight_bits(self):
        for length in range(9):
            for digits in itertools.product("01", repeat=length):
                bits = "".join(digits)
                for ones in ((), (-2, -1, 0, 1)):
                    self.check_program(bits, ones, limit=6)

    def test_random_program_traces(self):
        rng = random.Random(20261101)
        for _ in range(150):
            bits = "".join(rng.choice("01") for _ in range(rng.randrange(9, 97)))
            ones = {i for i in range(-5, 6) if rng.randrange(2)}
            self.check_program(bits, ones, limit=20)

    def test_all_neighbor_cases_across_origin(self):
        for head in range(-3, 4):
            for current, neighbor in itertools.product((0, 1), repeat=2):
                prefix = [("move", 1 if head > 0 else -1)] * abs(head)
                bits = self.encoder(prefix + [("nand", 1)])
                ones = {i for i, bit in ((head, current), (head + 1, neighbor)) if bit}
                self.check_program(bits, ones)

    def test_unbounded_growth_and_loops(self):
        for direction in (-1, 1):
            bits = self.encoder([("nand", 0), ("move", direction), ("branch", 0, 0)])
            reference, hosted = self.check_program(bits, limit=90)
            self.assertFalse(hosted.halted)
            self.assertEqual(len(reference.ones), 30)
            self.assertEqual(reference.head, direction * 30)
        self.check_program("11", limit=100)

    def test_branch_targets_and_truncated_operands(self):
        # Different instruction widths, both branch arms, backward and past-end.
        for target in (0, 1, 2, 3, 4, 10, 25):
            for ones in ((), (0,)):
                bits = self.encoder([("branch", target, 3), ("move", -1),
                               ("nand", 1), ("branch", 8, target)])
                for trim in range(4):
                    self.check_program(bits[:-trim] if trim else bits, ones, limit=8)

    def test_frame_contains_raw_bits_not_decoded_instructions(self):
        self.assertEqual(self.framer("01", {-1, 0}), self.expected_frame)
        self.assertNotEqual(self.framer("0"), self.framer("00"))
        self.assertEqual(self.decoder("0"), self.decoder("00"))

    def test_own_program_as_guest_prefix(self):
        # Real self-application: feed the interpreter's complete bits as source,
        # with a second framed guest as its data. Bound this deliberately: a full
        # second level is expensive with unary branches and repeated tape scans.
        nested_input = self.framer("0")
        reference = Machine(self.code, nested_input.copy())
        hosted = Machine(self.code, self.framer(self.bits, nested_input))
        self.boundary(hosted)
        for _ in range(12):
            reference.step()
            self.boundary(hosted)
        self.assertEqual(self.extract(hosted.ones), (reference.ones, reference.head))

    def test_reproducible_artifact(self):
        artifact = repo_path("artifacts/nand_tape/" + self.artifact_name + ".nand")
        self.assertEqual(artifact.read_text(encoding="ascii"), self.bits)
        report = self.measure(self.code)
        self.assertEqual(sum(report["bits_by_operation"].values()), len(self.bits))
        saved = repo_path("artifacts/nand_tape/" + self.artifact_name + "_metrics.json")
        self.assertEqual(json.loads(saved.read_text()), report)


if __name__ == "__main__":
    unittest.main()
