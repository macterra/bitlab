# Knot as a language for physical simulation

**Knot can implement any computable physical simulation, given an appropriate
encoding of the model's state and inputs.** The Rule 30 implementation is a
working example of the required structure: a program takes an encoded state,
computes its successor, and repeats that computation to produce a history.

Encoding a state as a bitstring is necessary for this interface, but is not
sufficient by itself. The state-update rule must also be computable, and the
encoded state and supplied inputs must contain the information needed to
determine the next state.

## The simulation contract

Let `s` be a finite bitstring representing a model's state, and let `F` be its
computable update function:

```text
s(t + 1) = F(s(t))
```

Model parameters, boundary conditions, time, and external inputs can be encoded
alongside the state when the update requires them. There is no requirement that
successive states have equal-length encodings; that is a choice made by our
current cellular-automaton example.

Knot's universality means there is a Knot program implementing any such
computable `F` on its valid state encodings. If `F` terminates on every reachable
state, a Knot program can compute any requested finite number of updates, given
sufficient resources:

```text
encoded initial state + update count
    -> Knot program
    -> encoded final state or complete finite history
```

This claim concerns expressiveness. It does not imply efficient execution, a
small compiled program, or completion within a particular machine's resource
budget. It also does not imply that every arbitrary Knot program returns a
valid state: all source bitstrings have semantics, but some computations diverge
or produce values outside the chosen output format.

## What the Rule 30 implementation demonstrates

The [Knot Rule 30 history program](examples/knot_rule30.md) represents a finite row of
cells directly as bits. Each new cell is computed from the previous row by:

```text
new[i] = old[i - 1] XOR (old[i] OR old[i + 1])
```

The row has fixed width and cells outside its boundaries are zero. The native
program parses an update count, applies the rule repeatedly, and concatenates
the resulting rows. One invocation produces the initial row and all requested
successors. Python supplies the encoded input and formats the output; it does
not calculate or iterate the generations.

Run the example with:

```sh
python3 -m examples.knot_rule30
```

The saved program is 2,042 bits, with the separate 261-bit Knot decoder providing
its execution semantics. The implementation and tests demonstrate state
representation, local interaction, synchronous updates, iteration, and output
of a finite history inside a Knot program.

Rule 30 is an exact discrete mathematical model here. This demonstration does
not establish that Rule 30 describes a particular physical system. Nor does
this single example prove universality: the general computational claim comes
from Knot preserving the universal SK combinator basis and application, as
described in the [language specification](knot.md).

## Applying the same structure to physical models

A model might encode particle positions and velocities, a lattice of field
values, or a finite collection of interacting components. Its update algorithm
would operate on those representations and construct the next encoded state.
If that algorithm is computable, Knot can implement it.

For a stochastic model, the update can additionally consume random bits, or
carry the state of a pseudorandom generator. The source of randomness and its
representation then form part of the simulation contract; universality alone
does not supply physical randomness.

## Exact models, approximations, and physical reality

A simulation can exactly implement the rules of a discrete model while still
being an approximation to a physical system. Continuous quantities generally
require finite-precision representations or other computable descriptions.
A finite bitstring cannot explicitly contain infinitely many arbitrary digits,
although some exact values have finite symbolic descriptions.

Faithful physical prediction therefore depends on more than the programming
language: the model's laws, initial and boundary data, discretization, numerical
accuracy, and available resources all matter. Knot can execute an algorithm;
it does not establish that the algorithm faithfully describes nature.

The supported claim is about **computable models and finite requested
computations**. Whether every physical process admits an exact computable
description is a separate question, unresolved by this implementation.
