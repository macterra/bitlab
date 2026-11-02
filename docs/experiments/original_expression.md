# Original expression-language experiment

The notation below belongs to the earlier `experiments/legacy/nand.py` interpreter. It is separate
from the NAND tape prototype.

```
00 = 0
01 = 1
1xy = (nand x y) = (not (and x y))
```

```
101x = (nand 1 x) = (not (and 1 x)) = (not x)
100x = (nand 0 x) = (not (and 0 x)) = (not 0) = 1

10000 = (not (and 0 0)) = (not 0) = 1
10001 = (not (and 0 1)) = (not 0) = 1
10100 = (not (and 1 0)) = (not 0) = 1
10101 = (not (and 1 1)) = (not 1) = 0

101100x = (not (nand 0 x) = (not 1) = 0
101101x = (not (nand 1 x) = (not (not x) = x

1011xy = (not (nand x y) = (and x y)
1101x101y = (nand (not x) (not y)) = (or x y)

1x101y = (nand x (not y)) = (not (and x (not y))) = (or (not x) y) = x -> y
1101xy = (nand (not x) y) = (not (and (not x) y)) = (or x (not y)) = x <- y

1011100xy = (not 1100xy) = (not (nand 100x y)) = (and 1 y) = y
```
