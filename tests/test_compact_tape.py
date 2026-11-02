import itertools
import unittest

import experiments.compact_self_host as host
from languages.compact_tape import decode, encode, number, offsets
from languages.nand_tape import Machine
from experiments.self_host import COUNTER_END
import tests.test_self_host as test_self_host


class CompactCodecTests(unittest.TestCase):
    def test_examples_and_leading_zeros(self):
        self.assertEqual([number(n) for n in range(5)],
                         ["0", "110", "11100", "11110", "1110100"])
        self.assertEqual(decode("111000"), [("branch", 0, 0)])
        self.assertEqual(decode("111"), [("branch", 0, 0)])
        self.assertEqual(decode("11111"), [("branch", 2, 0)])
        self.assertEqual(offsets("11100000"), [0, 6])

    def test_total_syntax_through_twelve_bits(self):
        for length in range(13):
            for digits in itertools.product("01", repeat=length):
                bits = "".join(digits)
                code = decode(bits)
                self.assertEqual(decode(encode(code)), code)
                self.assertEqual(len(offsets(bits)), len(code))
                for index, start in enumerate(offsets(bits)):
                    self.assertEqual(decode(bits[start:]), code[index:])
                self.assertIn(Machine(code).run(20), ("halted", "suspended"))


class CompactSelfInterpreterTests(test_self_host.SelfInterpreterTests):
    encoder = staticmethod(encode)
    decoder = staticmethod(decode)
    builder = staticmethod(host.build)
    framer = staticmethod(host.frame)
    extract = staticmethod(host.result)
    measure = staticmethod(host.metrics)
    width = host.WIDTH
    artifact_name = "compact_self_host"
    expected_frame = {4, 24, 22, 12, 14}

    def source_offsets(self, bits):
        return offsets(bits)

    def check_program(self, *args, **kwargs):
        reference, hosted = super().check_program(*args, **kwargs)
        ends = {p for p in hosted.ones if p % self.width == COUNTER_END}
        self.assertEqual(len(ends), 1)
        if not hosted.halted:
            self.assertEqual(ends, {COUNTER_END})
        return reference, hosted

    def test_huge_address_does_not_expand_to_unary(self):
        for ones in ((), (0,)):
            bits = encode([("branch", 2**64, 2**64)])
            reference = Machine(decode(bits), set(ones))
            reference.step()
            hosted = Machine(self.code, self.framer(bits, ones))
            # Repeated origin scans are quadratic in source length. Allow for
            # that real cost, but not anything proportional to the address value.
            self.assertEqual(hosted.run(10000000), "halted")
            self.assertEqual(self.extract(hosted.ones), (reference.ones, reference.head))
            self.assertLess(len(hosted.ones), 1000)

    def test_noncanonical_numbers_and_truncations(self):
        # Leading zero digits and incomplete digit pairs retain their source span.
        for zero in ("0", "100", "10100", "1010110"):
            for one in ("0", "100", "10100", "11100"):
                bits = "11" + zero + one + "0010100"
                for trim in range(5):
                    for ones in ((), (0, 1)):
                        self.check_program(bits[:-trim] if trim else bits, ones, limit=6)


if __name__ == "__main__":
    unittest.main()
