from __future__ import print_function, division
import sys
import random
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from io_functions import read_cache_from_file

import matplotlib
matplotlib.style.use("classic")


def print_stats(results):
    """Print statistics of the results."""

    count_if = lambda t: len([r for r in results if r.type==t])
    N_msmts = max(
                  max(len(r.measurement_types) for r in results),
                  max(len(r.responses) for r in results)
                 )
    if not N_msmts: N_msmts = 1

    N_normals    = count_if("NORMAL");    p_normals    = 100*N_normals/len(results)
    N_resets     = count_if("RESET");     p_resets     = 100*N_resets /len(results)
    N_changings  = count_if("CHANGING");  p_changings  = 100*N_changings /len(results)
    N_justrights = count_if("JUSTRIGHT"); p_justrights = 100*N_justrights /len(results)

    N_faulty_points = len([r for r in results if r.responses])
    p_faulty_points = 100*N_faulty_points/len(results)

    N_faulty_responses = sum(len(r.responses) for r in results)
    p_faulty_responses = 100*N_faulty_responses/(N_msmts*len(results))

    N_unique_responses = len(set( resp for r in results for resp in r.responses ))
    p_unique_responses = 100*N_unique_responses/N_faulty_responses

    N_unique_cropped = len(set( resp[:64] for r in results for resp in r.responses ))
    p_unique_cropped = 100*N_unique_cropped/N_faulty_responses

    print("Of {:d} points:\n".format(len(results))
         +"    {:d} ({:.2f}%) NORMAL\n"   .format(N_normals, p_normals)
         +"    {:d} ({:.2f}%) RESET\n"    .format(N_resets, p_resets)
         +"    {:d} ({:.2f}%) CHANGING\n" .format(N_changings, p_changings)
         +"    {:d} ({:.2f}%) JUSTRIGHT\n".format(N_justrights, p_justrights)
         +"\n"
         +"{:d} ({:.2f}%) have at least one faulty response\n".format(N_faulty_points, p_faulty_points)
         +"\n"
         +"When counting the {:d} measurements per sample, ".format(N_msmts)
         +"{:d} ({:.2f}%) have faulty responses\n".format(N_faulty_responses, p_faulty_responses)
         +"and there are {:d} ({:.2f}%) unique responses\n".format(N_unique_responses, p_unique_responses)
         +"             ({:d} ({:.2f}%) when cropped to hash size)\n".format(N_unique_cropped, p_unique_cropped)
         )


def plot_points(pointcache, dim1="x", dim2="y", dim3=None, types=["RESET", "NORMAL", "CHANGING", "JUSTRIGHT"]):
    """Plot points from the pointcache.
    Args:
        pointcache -- contains the points to plot
        dim1 -- the abcissa; 'X' by default
        dim2 -- the ordinate; 'Y' by default
        dim3 -- the applicate; implies 3D plot instead of 2D plot!
    """

    resets     = [u for u in pointcache if u.type == "RESET"]
    normals    = [u for u in pointcache if u.type == "NORMAL"]
    changings  = [u for u in pointcache if u.type == "CHANGING"]
    justrights = [u for u in pointcache if u.type == "JUSTRIGHT"]
    assert len(resets) + len(normals) + len(changings) + len(justrights) == len(pointcache)
    assert dim1 in ["x", "y", "intensity", "offset", "repetitions"]
    assert dim2 in ["x", "y", "intensity", "offset", "repetitions"]
    assert dim3 in ["x", "y", "intensity", "offset", "repetitions", None]

    fig = plt.figure()

    if not dim3:
        if dim1=="x":
            plt.xlim(-0.1, 1.1)
        if dim2=="y":
            plt.ylim(-0.1, 1.1)
            plt.gca().invert_yaxis()
        plt.xlabel(dim1)
        plt.ylabel(dim2)

        if "RESET" in types:
            plt.scatter([eval("u."+dim1) for u in resets],
                        [eval("u."+dim2) for u in resets],
                         c="b", marker="o", label="RESET")
        if "NORMAL" in types:
            plt.scatter([eval("u."+dim1) for u in normals],
                        [eval("u."+dim2) for u in normals],
                         c="g", marker="x", label="NORMAL")
        if "CHANGING" in types:
            plt.scatter([eval("u."+dim1) for u in changings],
                        [eval("u."+dim2) for u in changings],
                         c="y", marker="D", label="CHANGING")
        if "JUSTRIGHT" in types:
            plt.scatter([eval("u."+dim1) for u in justrights],
                        [eval("u."+dim2) for u in justrights],
                         c="r", marker="s", label="SUCCESS")
    else:
        ax = Axes3D(fig)
        ax.set_xlabel(dim1)
        ax.set_ylabel(dim2)
        ax.set_zlabel(dim3)
        if dim1=="x":
            ax.set_xlim(-0.1, 1.1)
        if dim2=="y":
            ax.set_ylim(-0.1, 1.1)
            ax.invert_yaxis()

        if "CHANGING" in types:
            ax.scatter([eval("u."+dim1) for u in changings], [eval("u."+dim2) for u in changings],
                       [eval("u."+dim3) for u in changings], c="y", marker="D", label="CHANGING")
        if "JUSTRIGHT" in types:
            ax.scatter([eval("u."+dim1) for u in justrights], [eval("u."+dim2) for u in justrights],
                       [eval("u."+dim3) for u in justrights], c="r", marker="s", label="SUCCESS")
        if "NORMAL" in types:
            ax.scatter([eval("u."+dim1) for u in normals], [eval("u."+dim2) for u in normals],
                       [eval("u."+dim3) for u in normals], c="g", marker="x", label="NORMAL")
        if "RESET" in types:
            ax.scatter([eval("u."+dim1) for u in resets], [eval("u."+dim2) for u in resets],
                       [eval("u."+dim3) for u in resets], c="b", marker="o", label="RESET")

    plt.grid()
    plt.legend()
    plt.show()


def fatal_usage():
    print(
"""usage: ./plot_cache.py cachefile COMMAND SUBSET-SPECIFIER

    COMMAND:
      `stats` for printing statistics
      `intensity`, `offset`, `repetitions` for choosing the Z-axis of 3D plot
    If not present, it defaults to 2D plotting.

    SUBSET-SPECIFIER:
      `range x-y` -- use only points indexed [x,y); if x or y aren't
                      specified, they default to 0 and -1, respectively
      `amount x`  -- use only x randomly selected points
""",
          file=sys.stderr)
    sys.exit(1)


if __name__=="__main__":

    if len(sys.argv) < 2:
        fatal_usage()

    cache = read_cache_from_file(sys.argv[1])

    if not cache:
        print("No data read!")
        sys.exit(0)

    print("Read {} cached points".format(len(cache)))

    if len(sys.argv) > 2:
        cmd = sys.argv[2].lower()
    else:
        cmd = None

    types = ["NORMAL", "RESET", "CHANGING", "JUSTRIGHT"]

    if "nonormal"   in sys.argv: types.remove("NORMAL")
    if "noreset"    in sys.argv: types.remove("RESET")
    if "nochanging" in sys.argv: types.remove("CHANGING")
    if "nojustright" in sys.argv: types.remove("JUSTRIGHT")

    if "range" in sys.argv:
        rng = sys.argv[sys.argv.index("range") + 1]
        start, end = rng.split("-")
        start = int(start) if start else 0;
        end   = int(end)   if end   else -1
        cache = list(cache)[start:end]

    # randomly pick `amount` points
    elif "amount" in sys.argv:
        amount = int(sys.argv[sys.argv.index("amount") + 1])
        cache = list(cache)
        random.shuffle(cache)
        cache = cache[:amount]

    if cmd and not cmd.startswith("no"):
        if cmd == "stats":
            print_stats(cache)
        if cmd.startswith("i"):
            plot_points(cache, dim1="x", dim2="y", dim3="intensity", types=types)
        if cmd.startswith("o"):
            plot_points(cache, dim1="x", dim2="y", dim3="offset", types=types)
        if cmd.startswith("r"):
            plot_points(cache, dim1="x", dim2="y", dim3="repetitions", types=types)
    else:
        plot_points(cache, types=types)
