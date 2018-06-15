from __future__ import print_function, division
import time
import sys

from xyz_table import *
from ga import *
from gui import GUI
from io_functions import *
from unit import *

import numpy as np
import random


commands = ["grid", "random", "algo"]


CACHEFILE = "cached.txt"
POPFILE   = "population.txt"
N_ITERS   = 50
POPSIZE   = 20

def grid_search(vcg, table,
                xrange=(0.0, 1.0),
                yrange=(0.0, 1.0),
                spatial_granul=21,
                irange=(0.0, 1.0),
                int_granul=21,
                offset_ms=[0.1, 2, 4, 6, 8, 10],
                repetitions=1):
    """
    Parameter search using grid scan.

    Arguments:
    ----------
        xrange, yrange, irange     -- pairs of (startval, endval)
        spatial_granul, int_granul -- granularity of the [startval, endval] interval

        offset_ms   -- a list of time offsets, in milliseconds
        repetitions -- the number of repetitions to use
    """

    num_to_visit = spatial_granul**2 * int_granul * len(offset_ms)
    print("Starting grid search of {} positions, for a total of {} measurements".format(spatial_granul**2, num_to_visit))

    offset_ms = [int(m * 100*500) for m in offset_ms]
    
    population = []
    even = False
    counter = 0
    t0 = time.time()
    for x in np.linspace(xrange[0], xrange[1], spatial_granul):
        even = not even
        for y in np.linspace(yrange[0], yrange[1], spatial_granul)[::1 if even else -1]:    # go the other way around every other turn
            for intensity in np.linspace(irange[0], irange[1], int_granul):
                for offset in offset_ms:
                    u = Unit()
                    u.x = x; u.y = y; u.intensity = intensity; u.offset = offset; u.repetitions = repetitions
                    evaluate_unit(vcg, table, u)

                    counter += 1
                    if counter%100 == 0 or counter == num_to_visit:
                        dt = time.time() - t0
                        done = float(counter)/num_to_visit
                        left = (dt/done) * (1-done)
                        print("Evaluated {}/{}, or {:.3f}% ({:.1f}s elapsed, {:.1f} left)".format(
                            counter, num_to_visit, 100*done, dt, left))
    return cache



def random_search(vcg, table, N):
    """
    Random parameter search; scans N points.

    Uses nearest-neighbor heuristic for finding shortest path.
    """

    scanned = []
    to_scan = [Unit() for _ in range(N)]
    u = None

    counter = 0
    t0 = time.time()

    while to_scan:

        # find next point
        if u is None:       # initial case
            u = to_scan[0]
        else:               # otherwise, nearest neighbor
            u = min((u.distance_to(x, xy_plane=True), x) for x in to_scan)[1]
        to_scan.remove(u)

        evaluate_unit(vcg, table, u)

        counter += 1
        if counter%10 == 0 or counter == N:
            dt = time.time() - t0
            done = float(counter)/N
            left = (dt/done) * (1-done)
            print("Evaluated {}/{}, or {:.3f}% ({:.1f}s elapsed, {:.1f} left)".format(
                    counter, N, 100*done, dt, left))



def algo_search(vcg, table):
    """Parameter search using own algorithm"""

    population = generate_population(POPSIZE)
    N_scanned = []

    print("Starting GA")
    t0 = tgen = time.time()
    for i in range(N_ITERS):
        print("Iteration {}".format(i+1))
        fits = evaluate_batch(vcg, table, population)
        population = selection_roulette(population, elite_size=1)
        print(fits)
        print("Mean={}, max={}".format(np.mean(fits), np.max(fits)))
        print("Iteration took {:.2f}s, total {:.2f}".format(time.time()-tgen, time.time()-t0))
        tgen = time.time()

    t1 = time.time()
    N_scanned.append(len(cache))

    print("Time elapsed GA/total: {}/{} s".format(t1-t0, t1-t0))
    print("Scanned points GA/total: {}/{}".format(N_scanned[0], sum(N_scanned)))
    print(" speed: {}s per point".format((t1-t0)/N_scanned[-1]))
    print("Starting searches around JUSTRIGHTs")

    for u in [u for u in cache if u.type=="JUSTRIGHT"]:
        # local search in SMALL cubes
        for i in range(10):
            u = copy.deepcopy(u)
            mutate_unit(u, p_mut=1.0, Q=CUBE_SIZE_SMALL)
            evaluate_unit(vcg, table, u)

    t3 = time.time()
    N_scanned.append(len(cache) - N_scanned[-1])
    print("{}s elapsed, {}s in total\n{} scanned points".format(t2-t1, t2-t0, len(cache)))
    print("Time elapsed local/total: {}/{} s".format(t2-t1, t2-t0))
    print("Scanned points local/total: {}/{}".format(N_scanned[1], sum(N_scanned)))
    print(" speed: {}s per point".format((t2-t1)/N_scanned[-1]))

    print("Total speed: {}s per point".format((t2-t0)/len(cache)))



def fatal_usage():
    print("Usage: python {:s} [grid | random N | algo]".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)



if __name__=="__main__":

    from vcg import *

    if not (len(sys.argv) >= 2 and sys.argv[1].lower() in commands):
        fatal_usage()

    cmd = sys.argv[1].lower()

    try:
        try:
            f = open("points.txt")
            table = XYTable(f)
            f.close()
        except:
            table = XYTable()
        table.connect()

        # set points if necessary
        if not table.origin:
            interface = GUI(table)
            interface.start()
        
        table.move_to_position(table.gen2coord(0,0))

        vcg = VCG()
        print("Have VCG")


        if cmd == "random":
            try:
                N = int(sys.argv[2])
                assert N >= 0
            except:
                fatal_usage()
            print("Starting random search")
            random_search(vcg, table, N)

        elif cmd == "grid":
            print("Starting grid search")
            cache = grid_search(vcg, table,
                spatial_granul=41,
                int_granul=21,
                offset_ms=[0.367, 0.368, 0.369, 0.370, 0.371, 0.372, 0.373, 0.374, 0.375]
                        )

        else:
            print("Starting own algorithm")
            algo_search(vcg, table)
            #algo2(vcg, table)


        # Print the timing stats
        N = lambda name: sum((
                               sum(m == name.upper() for m in u.measurements)
                                  if u.measurements
                                  else 5 * sum(name == u.type)
                             ) for u in cache)
        pct = lambda name: time_while[name]/N(name) if N(name) else 0.0
        tw = time_while
        print("Time spent moving: {:.3f}s\n".format(tw["moving"])
             +"Time spent optimizing path: {:.3f}s\n".format(tw["path"])
             +"Time spent while evcg_busy: {:.3f}s\n".format(tw["evcg_busy"])
             +"Time spent on RESETs: {:.3f}s ({:.3f}s per measurement)\n".format(tw["reset"], pct("reset"))
             +"Time spent on NORMALs: {:.3f}s ({:.3f}s per measurement)\n".format(tw["normal"], pct("normal"))
             +"Time spent on JUSTRIGHTs: {:.3f}s ({:.3f}s per measurement)\n".format(tw["justright"], pct("justright"))
             )
        
    except KeyboardInterrupt:
        print("Killed by KeyboardInterrupt")

    except Exception as e:
        import traceback
        traceback.print_exc()
        import ipdb; ipdb.set_trace()

    finally:
        # 0. stop the XY-table from moving
        table.stop()
        table.disconnect()

        # 1. save the corner points
        with open("points.txt","w") as f:
            table.write_to_file(f)

        # 2. write out (numbered) scan results
        print("Writing out scan results")
        write_cache_to_file(CACHEFILE, cache)
