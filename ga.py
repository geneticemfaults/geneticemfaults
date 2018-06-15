import numpy as np
import random
import time
import copy
from collections import OrderedDict
from binascii import unhexlify
from vcg import VCG_ReadTimeout, VCG_BusyTimeout
from tsp import find_shortest_hamilton_path_XYZ
from io_functions import read_cache_from_file
from unit import Unit, OFFSET_MIN, OFFSET_MAX, OFFSET_RANGE

P_MUT = 0.05
CUBE_SIZE = 0.1     # cutoff distance for "close"
CUBE_SIZE_SMALL = 0.02

RESPONSE_CORRECT = unhexlify(
    b"b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c9"
    b"1a7ec57647e3934057340b4cf408d5a56592f8274eec53f04c3fd10674a4addf5441a169a379b5d7"
    b"daf06b9f7cf8841453513acb4f6528e776df12d28608348c40e7943424989776bb403dce51a16423"
    b"33f95fcb9697e79a459e385510e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f827"
    b"4eec53f04c3fd10674a4addf5441a169a379b5d7daf06b9f7cf8841453513acb4f6528e776df12d2"
)

# Chip dimensions:
#   24mm * 24mm
# Repositioning precision:
#   0.05mm
#
# That gives us a 480*480 grid.
# Without explicitly introducing the grid,
#  we can just say that there's no point
#  in having an xy offset of less than 0.002 (=1/500)

XY_RESOLUTION = 500


cache = OrderedDict()

time_while = {
    "moving"    : 0.0,    # total time spent moving
    "path"      : 0.0,    # total time spent optimizing path
    "reset"     : 0.0,    # total time spent on RESET measurements
    "normal"    : 0.0,    # total time spent on NORMAL measurements
    "justright" : 0.0,    # total time spent on JUSTRIGHT measurements
    "evcg_busy" : 0.0,    # total time spent on evcg_busy interrupts
}



def generate_population(N):
    return [Unit() for i in range(N)]


def mutate_unit(solution, p_mut, Q=0.50):
    clip = lambda x: min(max(x,0.0),1.0)
    rand = random.random
    if rand() < p_mut: solution.x         = clip(solution.x+rand()*Q - Q/2)
    if rand() < p_mut: solution.y         = clip(solution.y+rand()*Q - Q/2)
    if rand() < p_mut: solution.intensity = clip(solution.intensity+rand()*Q - Q/2)
    if rand() < p_mut: solution.repetitions = random.randint(1,10)
    if rand() < p_mut:
        new_offs = solution.offset + rand()*OFFSET_RANGE - OFFSET_RANGE/2   # Q is percentage of range here
        new_offs = int(round(min(max(new_offs, OFFSET_MIN), OFFSET_MAX)))   # clip to range
        solution.offset = new_offs


def crossover(parent1, parent2):
    child = Unit()
    child.x           = random.random()*(parent1.x - parent2.x) + parent2.x
    child.y           = random.random()*(parent1.y - parent2.y) + parent2.y
    child.intensity   = random.random()*(parent1.intensity - parent2.intensity) + parent2.intensity
    o1 = min(parent1.offset, parent2.offset)
    o2 = max(parent1.offset, parent2.offset)
    child.offset      = random.choice(range(o1, o2+1))
    r1 = min(parent1.repetitions, parent2.repetitions)
    r2 = max(parent1.repetitions, parent2.repetitions)
    child.repetitions = random.choice(range(r1, r2+1))
    return child


def selection_roulette(population, elite_size=4, mutate=mutate_unit):
    """Roulette selection with elitism"""
    N = len(population)
    newpop = []

    fits = np.array([float(u.fitness) for u in population])
    if fits.min()<0:
        fits -= fits.min()
    fits /= fits.sum()

    parents1 = np.random.choice(population, size=N-elite_size, p=fits)
    parents2 = np.random.choice(population, size=N-elite_size, p=fits)
    for par1, par2 in zip(parents1, parents2):
        child = crossover(par1, par2)
        mutate(child, P_MUT)
        newpop += [child]

    newpop += sorted(population, reverse=True)[:elite_size]

    return newpop


def evaluate_batch(vcg, table, population):

    uncached = [u for u in population if u not in cache]
    if not uncached:
        return [u.fitness for u in population]

    #                        #
    #   path optimization:   #
    #                        #
    t0 = time.time()
    best_sequence = find_shortest_hamilton_path_XYZ(uncached, table)
    to_visit = np.array(uncached)[best_sequence]
    time_while["path"] += time.time() - t0

    for unit in population:
        if unit in cache:
            unit.fitness = cache[unit]


    for unit in to_visit:
        evaluate_unit(vcg, table, unit)

    return [u.fitness for u in population]


def evaluate_unit(vcg, table, unit, num_measurements=5):
    """Evaluates a single point, with `num_measurements` measurements"""

    abs_coords = table.gen2coord(unit.x, unit.y)
    table.move_to_position(abs_coords)

    t0 = time.time()
    table.wait()
    time_while["moving"] += time.time() - t0

    measurements = []
    responses = []

    i=0
    stuckcounter = 0
    while i < num_measurements:     # do N measurements (plus any repeated ones)
        i += 1
        try:
            t0 = time.time()
            response = vcg.glitch(intensity=unit.intensity, offset=unit.offset, repeat=unit.repetitions)

            if response == RESPONSE_CORRECT:
                measurements.append("NORMAL")
                vcg.reset()
                time_while["normal"] += time.time() - t0
            else:
                measurements.append("JUSTRIGHT")
                responses.append(response)
                vcg.reset()
                time_while["justright"] += time.time() - t0

        except VCG_BusyTimeout:
            # if VCG gets stuck in evcg_busy, we
            # reset the board and repeat the measurement
            vcg.reset()
            i -= 1
            print("Reset the board")
            time_while["evcg_busy"] += time.time() - t0

            stuckcounter += 1
            if stuckcounter % 10 == 0:
                import ipdb; ipdb.set_trace()

        except VCG_ReadTimeout:
            measurements.append("RESET")
            vcg.reset()
            time_while["reset"] += time.time() - t0

    assert len(measurements) == num_measurements
    unit.measurements = measurements
    unit.responses = responses


    # classify into classes
    if not all([measurements[0] == m for m in measurements]):
        unit.type = "CHANGING"
        N_normal     = sum(1 for m in measurements if m == "NORMAL")
        N_reset      = sum(1 for m in measurements if m == "RESET")
        N_justright  = sum(1 for m in measurements if m == "JUSTRIGHT")
        unit.fitness = 4 + 1.2*N_justright + 0.2*N_normal + 0.5*N_reset
    else:
        if measurements[0] == "NORMAL":
            unit.type = "NORMAL"
            unit.fitness = 2
        elif measurements[0] == "JUSTRIGHT":
            unit.type = "JUSTRIGHT"
            unit.fitness = 10
        else:
            unit.type = "RESET"
            unit.fitness = 5

    cache[unit] = unit.fitness
