# Triage calculus: a structurally different runtime

This experiment leaves lambda-calculus execution and variable indices behind.
It implements the triage variant of tree calculus, with a single native operator
and five local reduction rules. The measured native self-interpreters are
**329 bits for quoted tree input** and **987 bits for raw binary input**.
Neither is a shorter raw-bit interpreter than the 174-bit functional baseline.

The model comes from Barry Jay's tree calculus and Johannes Bader's triage
variant. The primitive rules below follow
[Bader's specification](https://treecalcul.us/specification/). This repository
adds its binary/EOF convention, lazy machine, generated interpreters, measurements,
and tests; it does not claim discovery of the calculus.

## Runtime and binary source

Write `T` for the sole operator, and associate application to the left:

```text
T T y z             -> y
T (T x) y z         -> x z (y z)
T (T w x) y T       -> w
T (T w x) y (T u)   -> x u
T (T w x) y (T u v) -> y u v
```

The final three cases inspect tree shape. No parser, interpreter, lambda binder,
substitution operation, or named combinator is a guest primitive.

The implementation uses lazy head reduction. It exposes only the root shapes
needed by a rule, leaving child expressions unevaluated until needed. A weak-head
result is a leaf, stem, or fork; this does not imply its children have full normal
forms. A separate normalization utility is used for finite semantic checks.

Source uses the prefix code `0 = T`, `1 f x = application(f,x)`. At EOF a missing
subtree becomes `T`. Once one complete tree has been read, its suffix is ignored.
Thus every finite bitstring denotes a finite closed expression, including empty
and truncated strings. Every existing `1` creates only two subtree obligations,
and EOF closes obligations with leaves, so source construction terminates.
Execution of the resulting expression need not terminate.

## Constructive universality

The standard combinators are represented entirely with T:

```text
K = T T
S = T (T (K T)) T
I = T (T K) T
```

The first rule gives `K x y -> x`. The stem rule gives
`S x -> (K T) x (T x) -> T (T x)`, and hence
`S x y z -> x z (y z)`. Similarly `I x -> K x (T x) -> x`.
This embeds SK combinatory logic and establishes universality. K, S, and I cost
3, 11, and 9 native bits, respectively, with every occurrence expanded.

The development compiler removes lambda notation by bracket abstraction using
these identities. It emits only T and application, and uses `S a b = T (T a) b`
directly. There is no hidden S/K opcode or eta-based replacement. The lambda
notation is an authoring convenience; the native runtime contains no lambdas.

## Two explicit input contracts

The structural interpreter consumes a **quoted syntax tree**:

```text
quote(T)   = T
quote(f x) = T quote(f) quote(x)
```

The host quote operation merely constructs data; it does not evaluate it.
However, it receives an already parsed expression, so the 329-bit measurement
does not include decoding raw bits. The interpreter maps a quoted leaf to T
and a quoted application to application of the recursively interpreted children.
An induction on the syntax tree establishes this simulation, without requiring
the represented computation to terminate.

The 987-bit raw interpreter includes a continuation-passing binary parser with
the same virtual-leaf EOF and ignored-suffix rules as the host codec. Its input
is a plain list of bits, represented natively:

```text
nil        = T
cons h t   = T h t
bit 0      = T
bit 1      = T T
```

This mapping depends only on the bits. It neither parses nor executes source.
Output uses the same representation. Program and external input are separately
framed, as in the functional experiment, but their concrete representations
differ. A case distinction can inspect the list's root directly using the native
tree rules.

The parser's leaf case returns T and the remaining source to its continuation.
Its application case parses two subtrees in sequence, applies their results,
then passes the remaining source onward. Its empty-list case returns T and an
empty suffix. Induction over the finite host parsing derivation therefore gives
the same resulting computation for every raw source, including truncations.

Let `P` be that native decoder, and `q = encode(P)`. Since the codec decodes its
own complete encoding exactly, `P(bitlist(q))` computes P. Giving it a raw guest
and external input consequently simulates the guest. The same argument, with
`quote` instead of bit-list construction, establishes structural self-interpretation.

## Measurements, tests, and limits

```sh
python3 triage.py --report triage_metrics.json --emit triage_self.bits --emit-structural triage_structural.bits
python3 triage.py --run 110101000 --input 101
python3 -m unittest -v test_triage
```

The second command executes the native identity program. The report hashes both
interpreter artifacts and the full Python reference module. That module includes
development utilities; its byte count is provenance, not a minimized formal
specification or a cross-runtime complexity lower bound.

The tests compare the machine with an independent small-step rule implementation,
exercise all five rules and the universal basis, compare the native binary parser
with the host codec on all 127 strings through six bits, and regenerate artifacts.
Both interpreters execute their own native programs. The raw interpreter also
completes a bit-list transformation from `101` to `001` through self-interpretation.

For identity on `101`, direct use of the raw decoder takes 8,021 machine steps;
one complete self-interpretation level takes 1,464,435. The quoted-tree route
takes 2,006 and 576,020 respectively. These counts belong to this implementation,
and are not comparable unit-for-unit with the lambda or tape machines.
A separate two-level quoted-tree run exhausted 100 million steps without
producing output. This is a fuel limit, not evidence of divergence; the regression
test requires the completed one-level case.

This first compiler is deliberately straightforward and its native sizes are
upper bounds, not minima. The useful architectural distinction is explicit
structural reflection with very small local rules. Quoted data makes decoding
cheaper, but the raw parser still has a substantial cost. That distinction is
preserved in the research frontier rather than treating the two interpreter
sizes as interchangeable.
