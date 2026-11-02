
def binary(s):
    return "0" + str(s) if s<=1 else binary(s>>1) + "0" + str(s&1)

for c in "hello world":
    print(binary(ord(c)), end="")

