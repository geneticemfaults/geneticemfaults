import numpy as np

def total_distance(solution, cities, norm="euclidean", cycle=False):
    """Calculates the total distance between cities for the given ordering.
    Args:
        solution -- the ordering
        cities   -- the cities (as np.ndarrays)
        cycle    -- if `True`, the distance is that of a cycle; else, a path
        norm     -- "euclidean" or "max"
    """
    if norm == "euclidean": norm = np.linalg.norm
    elif norm == "max"    : norm = max
    else: raise ValueError("Invalid value for parameter `norm`: " + str(norm))

    if cycle:
        cycle = solution[:] + [solution[0]]
        temp  = cities[cycle]
    else:
        temp = cities[solution]

    return sum(norm(temp[i]-temp[i-1]) for i in range(1,len(temp)))



def tsp_greedy(cities, norm="euclidean"):
    """Finds a greedy solution to the TSP, starting from the first city
    in the list given.

    The result is the same for both a circuit and a path, so there are no
    separate parameters for this.

    `norm` parameters are the same as for `total_distance`.
    """
    if norm == "euclidean": norm = np.linalg.norm
    elif norm == "max"    : norm = max
    else: raise ValueError("Invalid value for parameter `norm`: " + str(norm))

    cities = np.array(cities)
    assert len(cities.shape)==2

    point = list(range(len(cities)))

    path = [0]
    remaining = list(range(1, len(cities)))
    while remaining:
        curr = path[-1]
        nearest = sorted([(norm(cities[curr] - cities[i]), i) for i in remaining])
        nearest = nearest[0][1]
        path.append(nearest)
        remaining.remove(nearest)

    return path



def swap_2opt(tour, i, j):
    """Returns `tour` with the part from node i to node j (inclusive) reversed.
    """
    return tour[:i] + tour[i:j+1][::-1] + tour[j+1:]



def tsp_2opt(cities, init=None, cycle=False):
    """Returns a 2-optimal tour over the cities.

    If given, `init` is used for the starting point.
    """

    cities = np.array(cities)
    assert len(cities.shape)==2

    if init: tour = init
    else:    tour = list(range(len(cities)))

    bestdist = total_distance(tour, cities, cycle=True)

    # Try the 2-opt swap for every pair of edges.
    # When there's no improving swaps left, the tour is 2-optimal.
    improved = True
    while improved:
        improved = False

        # if we're optimizing a path, we don't touch the first node
        start = 0 if cycle else 1

        for i in range(start,len(cities)):
            for j in range(i+1, len(cities)):
                candidate = swap_2opt(tour, i, j)
                newdist = total_distance(candidate, cities, cycle=True)

                if newdist < bestdist:
                    tour = candidate
                    bestdist = newdist
                    improved = True
                    break

            if improved: break

    return tour


def find_shortest_hamilton_path_XYZ(uncached_solutions, table):
    """Finds shortest Hamilton path in the XYZ-table parameter space, with max-norm as distance.
        
        Since all motors are roughly the same speed, max-norm corresponds
        to actual time taken.

        Uses a greedy algorithm, followed by 2-opt.
    """

    cities = [table.get_position()] + [table.gen2coord(u.x, u.y) for u in uncached_solutions]
    cities = np.array([(c.x, c.y, c.z) for c in cities])

    assert len(cities.shape)==2 and cities.shape[1]==3

    greedy_solution = tsp_greedy(cities, norm="max")
    solution = tsp_2opt(cities, init=greedy_solution)

    solution = [x-1 for x in solution][1:]            # remove the current position from result

    return solution
