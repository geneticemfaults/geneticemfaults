# -*- coding: utf-8 -*-
import random

OFFSET_MIN = 367 * 500  # 370 µs
OFFSET_MAX = 375 * 500  # 373 µs
OFFSET_RANGE = OFFSET_MAX - OFFSET_MIN
REP_MIN = 1
REP_MAX = 1

class Unit:
# a solution is:
#   - a position (x,y) where x,y in [0,1]
#   - glitch offset/delay (when does it start)
#   - glitch intensity
#   - repetitions
    def __init__(self, repr=None):
        if not repr:
            self.x           = random.random()
            self.y           = random.random()
            self.intensity   = random.random()
            self.offset      = random.randint(OFFSET_MIN, OFFSET_MAX)
            self.repetitions = random.randint(REP_MIN, REP_MAX)
            self.fitness = None
            self.type    = None
        else:
            repr = repr.strip("()").split(",")
            self.x         = float(repr[0])
            self.y         = float(repr[1])
            self.intensity = float(repr[2])
            self.offset      = int(repr[3])
            self.repetitions = int(repr[4])
            self.type        = repr[5]
            if len(repr)==7:
                if repr[6]=="None":
                    self.fitness = None
                else:
                    self.fitness = float(repr[6])

    def __str__(self):
        return "(x={:4f}, y={:4f}, intensity={:4f}, offset={:d}, repetitions={:d}, type={})".format(
                self.x, self.y, self.intensity, self.offset, self.repetitions, self.type)

    def __repr__(self):
        return "({:.16f},{:.16f},{:.16f},{:d},{:d},{:s},{})".format(
                self.x, self.y, self.intensity, self.offset, self.repetitions, self.type, self.fitness)

    def __lt__(self, other):
        return self.fitness < other.fitness

    def __eq__(self, other):
        return (self.x == other.x and self.y == other.y
                and self.intensity == other.intensity
                and self.offset == other.offset
                and self.repetitions == other.repetitions)

    def __hash__(self):
        return hash((self.x, self.y, self.intensity, self.offset, self.repetitions))

    def distance_to(self, point, xy_plane=False):
        assert type(point) is type(self), "Cannot compare to another type!"
        if xy_plane:
            return ((point.x-self.x)**2 + (point.y-self.y)**2)**0.5

        return (
           (point.x-self.x)**2
         + (point.y-self.y)**2
         + (point.intensity  -self.intensity  )**2
         +((point.offset     -self.offset     )/float(OFFSET_MAX - OFFSET_MIN))**2
         #+((point.repetitions-self.repetitions)/float(REP_MAX    - REP_MIN   ))**2
        )**0.5
