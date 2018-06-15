from __future__ import print_function
from unit import Unit
from collections import OrderedDict
import binascii
import struct
                                                               # In Python 3:
hex_frombytes = lambda b: binascii.hexlify(b).decode("ascii")  # bytes.hex
bytes_fromhex = lambda b: binascii.unhexlify(b)                # bytes.fromhex


def write_cache_to_file(filename, cache):
    with open(filename, "w") as f:

        # version number
        print("v2", file=f)

        # numbered scanned points
        for (i, unit) in enumerate(cache):
            s = "{:d} {:s}".format(i, repr(unit))

            if unit.responses:
                s += " "
                s += " ".join(hex_frombytes(resp) for resp in unit.responses)

            if hasattr(unit, "measurements"):
                measurements = unit.measurements
                if measurements and not all(measurements[0] == m for m in measurements):
                    s += " $ " + " ".join(measurements)

            print(s, file=f)


def read_cache_from_file(filename):
    cache = OrderedDict()
    try:
        with open(filename) as f:
            lines = [l.strip() for l in f.readlines()]
    except:
        return cache

    # old format
    if lines[0] == "v0" or lines[0].startswith("("):
        for line in lines[1:]:
            unit = Unit(line)
            cache[unit] = unit.fitness

    # new format, looks like:
    # "number unit_repr response ... response"
    elif lines[0] == "v1":
        for line in lines[1:]:
            splat = line.split()
            assert len(cache) == int(splat[0])                       # ordinal number
            unit = Unit(splat[1])                                    # repr
            unit.responses = [bytes_fromhex(r) for r in splat[2:]]   # responses, if any
            cache[unit] = unit.fitness

    elif lines[0] == "v2":
        for line in lines[1:]:
            splat = line.split()
            assert len(cache) == int(splat[0])
            unit = Unit(splat[1])

            if "$" in splat:
                Rs = splat[2 : splat.index("$")]
                Ms = splat[splat.index("$") + 1 : ]
            else:
                Rs = splat[2:]
                Ms = []

            unit.responses = [bytes_fromhex(r) for r in Rs]    # responses, if any
            unit.measurement_types = Ms                        # measurement types, if any
            cache[unit] = unit.fitness

    else:
        raise NotImplementedError("Unsupported format")

    return cache



def write_population_to_file(filename, population):
    with open(filename, "w") as f:
        for unit in population:
            print(repr(unit), file=f)



def read_population_from_file(filename, popsize):
    try:
        with open(filename) as f:
            lines = [l.strip() for l in f.readlines()]
        return [Unit(line) for line in lines]
    except:
        return [Unit() for i in range(popsize)]



def write_responses_to_file(filename, responses, cropped=False):
    with open(filename, "wb") as f:
        # First 4B are little-endian number of faults
        f.write(struct.pack("<I", len(responses)))
        for r in responses:
            f.write(r)
