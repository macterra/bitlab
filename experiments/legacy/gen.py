import sys

class NandGenesis:
    def __init__(self):
        self.raw_dna = [] # Stores the Unary values (u_a, u_b)
        self.netlist = [] # The final resolved connections

    def parse_bitstream(self, bitstring):
        """
        Parses a string of '0's and '1's into raw gene pairs.
        Rule: Unary encoding. '1110' -> 3. Pairs of numbers define a gate.
        """
        current_count = 0
        current_pair = []

        # Pre-process: Remove whitespace just in case
        clean_bits = bitstring.strip().replace(" ", "").replace("\n", "")

        for bit in clean_bits:
            if bit == '1':
                current_count += 1
            elif bit == '0':
                # Delimiter found, commit the number
                current_pair.append(current_count)
                current_count = 0 # Reset counter

                # If we have a pair (Input A, Input B), commit the gate
                if len(current_pair) == 2:
                    self.raw_dna.append(tuple(current_pair))
                    current_pair = []
            else:
                # Ignore non-binary characters
                pass

        # --- HANDLING TERMINATION ---
        # Implicit Closure: If the stream ends abruptly, we assume 0s.
        # Case 1: Ended with '111' (pending count) -> treat as '1110'
        if current_count > 0:
            current_pair.append(current_count)

        # Case 2: Ended with a half-defined gate (Input A only) -> Input B is 0
        if len(current_pair) == 1:
            current_pair.append(0)
            self.raw_dna.append(tuple(current_pair))

    def compile_topology(self):
        """
        Applies the 'Live Wire' Modulo rule.
        Converts raw unary requests into actual indices based on Universe Size N.
        """
        N = len(self.raw_dna)
        if N == 0:
            return []

        self.netlist = []
        for i, (u_a, u_b) in enumerate(self.raw_dna):
            # The Modulo Operator makes this robust.
            # It wraps infinite unary numbers into the finite universe.
            # This allows forward references (wrapping around) and loops.

            conn_a = u_a % N
            conn_b = u_b % N

            self.netlist.append((conn_a, conn_b))

        return self.netlist

    def run_simulation(self, cycles=10):
        """
        Runs the network to prove it is valid.
        Output: The binary state of Gate 0 over time.
        """
        N = len(self.netlist)
        if N == 0: return "Empty Universe"

        # Initial state: All 0
        state = [0] * N
        output_signature = ""

        #print(f"\n--- Simulating Universe (Size {N}) ---")
        for t in range(cycles):
            # 1. Read State of Gate 0 (The Universe Output)
            output_signature += str(state[0])

            # 2. Compute Next State
            next_state = [0] * N
            for i in range(N):
                src_a, src_b = self.netlist[i]
                val_a = state[src_a]
                val_b = state[src_b]

                # NAND Operation
                if val_a == 1 and val_b == 1:
                    next_state[i] = 0
                else:
                    next_state[i] = 1

            state = next_state

        return output_signature

# --- MAIN EXECUTION ---

def generate_universe_from_string(input_str):
    genesis = NandGenesis()
    genesis.parse_bitstream(input_str)
    netlist = genesis.compile_topology()

    print(f"Input Stream: {input_str}")
    print(f"Universe Size: {len(netlist)} gates")
    print("\nGenerated Netlist (Gate Index: Input A, Input B):")

    for i, (a, b) in enumerate(netlist):
        raw_a, raw_b = genesis.raw_dna[i]
        print(f"Gate {i}: NAND(Gate {a}, Gate {b}) \t[Raw Gene: ({raw_a}, {raw_b})]")

    sig = genesis.run_simulation(15)
    print(f"Output Signature (Gate 0): {sig}")
    print("-" * 40)

# Test Case 1: The one you provided
# (3, 2), (4, 1), (0, 0) -> Should resolve Modulo 3
generate_universe_from_string("111011011110100")

# Test Case 2: A simple oscillator (Self-reference)
# 100 -> (1, 0). Size=1. 1%1=0, 0%1=0. Gate 0: NAND(0, 0) -> NOT(0).
generate_universe_from_string("100")

# Test Case 3: "Pi" / Random Noise / Forward References
# Note how 11111 (5) wraps around in a small universe
generate_universe_from_string("1011101011111000110")
