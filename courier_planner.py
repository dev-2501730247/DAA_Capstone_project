"""
Mini-Courier Planner  --  DAA Capstone (ETCCDA302)

Pipeline:
  1. Sort parcels by deadline / priority      (Merge Sort, O(n log n))
  2. Choose parcels for one trip              (0/1 Knapsack DP, O(n*W))
  3. Shortest paths between stops             (Dijkstra, O((V+E) log V))
  4. Delivery route                           (Nearest-Neighbor TSP approx, O(k^2))
  5. Benchmark each step on growing inputs

Usage:
    python courier_planner.py demo        # small dataset, full trace
    python courier_planner.py benchmark   # runtime tests + chart
    python courier_planner.py all         # both
"""
import heapq
import itertools
import json
import random
import sys
import time
from dataclasses import dataclass, asdict

DEPOT = 0  # node 0 is always the courier depot


# ----------------------------------------------------------------------
# PHASE 1: DATA DESIGN
# ----------------------------------------------------------------------
@dataclass
class Parcel:
    pid: int        # parcel id
    dest: int       # destination node in the city graph
    weight: int     # kg (integer, needed for DP table)
    value: int      # priority value (1-100); higher = more important
    deadline: int   # hours from now; smaller = more urgent


def generate_graph(n_nodes, extra_edges_factor=2, seed=1):
    """Connected weighted undirected graph as adjacency dict {u: [(v, w), ...]}.
    A random spanning tree guarantees connectivity; extra edges add alternatives."""
    rnd = random.Random(seed)
    adj = {i: [] for i in range(n_nodes)}
    seen = set()

    def add(u, v, w):
        if u == v or (min(u, v), max(u, v)) in seen:
            return
        seen.add((min(u, v), max(u, v)))
        adj[u].append((v, w))
        adj[v].append((u, w))

    for v in range(1, n_nodes):                      # spanning tree
        add(v, rnd.randrange(0, v), rnd.randint(1, 20))
    for _ in range(n_nodes * extra_edges_factor):    # extra roads
        add(rnd.randrange(n_nodes), rnd.randrange(n_nodes), rnd.randint(1, 20))
    return adj


def generate_parcels(n_parcels, n_nodes, seed=2):
    rnd = random.Random(seed)
    return [Parcel(i + 1, rnd.randrange(1, n_nodes), rnd.randint(1, 15),
                   rnd.randint(1, 100), rnd.randint(1, 48))
            for i in range(n_parcels)]


# ----------------------------------------------------------------------
# PHASE 2a: SORTING (Merge Sort - stable, guaranteed O(n log n))
# ----------------------------------------------------------------------
def merge_sort(items, key):
    """Stable merge sort. Returns a new sorted list."""
    if len(items) <= 1:
        return items[:]
    mid = len(items) // 2
    left, right = merge_sort(items[:mid], key), merge_sort(items[mid:], key)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):   # <= keeps it stable
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out


def insertion_sort(items, key):
    """O(n^2) baseline used only for runtime comparison."""
    a = items[:]
    for i in range(1, len(a)):
        cur, j = a[i], i - 1
        while j >= 0 and key(a[j]) > key(cur):
            a[j + 1] = a[j]; j -= 1
        a[j + 1] = cur
    return a


def sort_parcels(parcels):
    """Earliest deadline first; ties broken by higher priority value."""
    return merge_sort(parcels, key=lambda p: (p.deadline, -p.value))


# ----------------------------------------------------------------------
# PHASE 2b: 0/1 KNAPSACK (Dynamic Programming)
# ----------------------------------------------------------------------
def knapsack(parcels, capacity):
    """Pick parcels maximizing total priority value with total weight <= capacity.
    dp[i][w] = best value using first i parcels with capacity w.
    Returns (best_value, selected_parcels, dp_table)."""
    n = len(parcels)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        p = parcels[i - 1]
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]                        # skip parcel
            if p.weight <= w:                              # or take it
                dp[i][w] = max(dp[i][w], dp[i - 1][w - p.weight] + p.value)
    # backtrack to recover chosen parcels
    chosen, w = [], capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            chosen.append(parcels[i - 1])
            w -= parcels[i - 1].weight
    chosen.reverse()
    return dp[n][capacity], chosen, dp


# ----------------------------------------------------------------------
# PHASE 3a: DIJKSTRA
# ----------------------------------------------------------------------
def dijkstra(adj, src):
    """Returns (dist, prev). Min-heap implementation, O((V+E) log V)."""
    dist = {u: float("inf") for u in adj}
    prev = {u: None for u in adj}
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue                                   # stale entry
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v], prev[v] = nd, u
                heapq.heappush(pq, (nd, v))
    return dist, prev


def path_to(prev, target):
    path = []
    while target is not None:
        path.append(target)
        target = prev[target]
    return path[::-1]


# ----------------------------------------------------------------------
# PHASE 3b: NEAREST-NEIGHBOR TSP (approximation)
# ----------------------------------------------------------------------
def distance_matrix(adj, stops):
    """Shortest-path distance between every pair of stops (Dijkstra from each)."""
    dist, prevs = {}, {}
    for s in stops:
        dist[s], prevs[s] = dijkstra(adj, s)
    return dist, prevs


def nearest_neighbor_route(dist, stops, start=DEPOT):
    """Greedy: always go to the closest unvisited stop, then return to depot.
    O(k^2). Not optimal, but a fast heuristic."""
    unvisited = set(stops) - {start}
    route, cur, total = [start], start, 0
    while unvisited:
        nxt = min(unvisited, key=lambda s: dist[cur][s])
        total += dist[cur][nxt]
        route.append(nxt); unvisited.remove(nxt); cur = nxt
    total += dist[cur][start]
    route.append(start)
    return route, total


def brute_force_route(dist, stops, start=DEPOT):
    """Exact TSP by trying every order - only for tiny inputs, to measure
    how close nearest-neighbor gets to optimal."""
    others = [s for s in stops if s != start]
    best, best_len = None, float("inf")
    for perm in itertools.permutations(others):
        order = [start, *perm, start]
        length = sum(dist[a][b] for a, b in zip(order, order[1:]))
        if length < best_len:
            best, best_len = order, length
    return best, best_len


def expand_route(prevs, route):
    """Turn the stop-to-stop route into the full road-by-road node path."""
    full = [route[0]]
    for a, b in zip(route, route[1:]):
        full.extend(path_to(prevs[a], b)[1:])
    return full


# ----------------------------------------------------------------------
# FULL PIPELINE
# ----------------------------------------------------------------------
def plan_trip(adj, parcels, capacity, verbose=False):
    """Runs all steps, returns result dict with per-step timings (seconds)."""
    t = {}
    c = time.perf_counter()
    sorted_p = sort_parcels(parcels)
    t["sort"] = time.perf_counter() - c

    c = time.perf_counter()
    best_val, chosen, dp = knapsack(sorted_p, capacity)
    t["knapsack"] = time.perf_counter() - c

    stops = sorted({DEPOT, *(p.dest for p in chosen)})
    c = time.perf_counter()
    dist, prevs = distance_matrix(adj, stops)
    t["dijkstra"] = time.perf_counter() - c

    c = time.perf_counter()
    route, length = nearest_neighbor_route(dist, stops)
    t["tsp"] = time.perf_counter() - c

    return dict(sorted=sorted_p, value=best_val, chosen=chosen, dp=dp, stops=stops,
                dist=dist, prevs=prevs, route=route, length=length, times=t)


def print_parcels(title, parcels):
    print(f"\n{title}")
    print(f"{'ID':>4} {'Dest':>5} {'Wt':>4} {'Value':>6} {'Deadline':>9}")
    for p in parcels:
        print(f"{p.pid:>4} {p.dest:>5} {p.weight:>4} {p.value:>6} {p.deadline:>9}")


# ----------------------------------------------------------------------
# DEMO (small dataset, readable trace)
# ----------------------------------------------------------------------
def demo():
    print("=" * 60, "\nDEMO: small dataset (10 nodes, 12 parcels, capacity 30 kg)\n" + "=" * 60)
    adj = generate_graph(10, seed=7)
    parcels = generate_parcels(12, 10, seed=3)
    capacity = 30

    print("\nCity graph (node: [(neighbor, km), ...])")
    for u in adj:
        print(f"  {u}: {adj[u]}")

    res = plan_trip(adj, parcels, capacity)
    print_parcels("All parcels (input)", parcels)
    print_parcels("Sorted by deadline, then priority (Merge Sort)", res["sorted"])

    print(f"\nKnapsack DP: capacity = {capacity} kg")
    print("DP table (last rows, columns = capacity 0..%d):" % capacity)
    for i in range(max(0, len(res['dp']) - 4), len(res['dp'])):
        print(f"  i={i:>2}: {res['dp'][i]}")
    print(f"Best total priority value = {res['value']}")
    print_parcels("Selected parcels for this trip", res["chosen"])
    print(f"Total weight = {sum(p.weight for p in res['chosen'])} kg")

    print("\nDelivery stops (incl. depot):", res["stops"])
    print("\nShortest paths from depot (Dijkstra):")
    for s in res["stops"]:
        if s != DEPOT:
            print(f"  0 -> {s}: dist={res['dist'][DEPOT][s]}, "
                  f"path={path_to(res['prevs'][DEPOT], s)}")

    print("\nNearest-Neighbor route:", res["route"])
    print("Full road path        :", expand_route(res["prevs"], res["route"]))
    print("Route length          :", res["length"], "km")

    if len(res["stops"]) <= 9:
        opt, opt_len = brute_force_route(res["dist"], res["stops"])
        print(f"Optimal (brute force) : {opt} length={opt_len} km")
        print(f"Approximation ratio   : {res['length'] / opt_len:.3f}")

    with open("sample_dataset.json", "w") as f:
        json.dump({"graph": {str(k): v for k, v in adj.items()},
                   "parcels": [asdict(p) for p in parcels],
                   "capacity": capacity}, f, indent=2)
    print("\nSaved sample_dataset.json")


# ----------------------------------------------------------------------
# PHASE 4: BENCHMARK
# ----------------------------------------------------------------------
def benchmark():
    print("=" * 60, "\nBENCHMARK\n" + "=" * 60)
    sizes = [10, 50, 100, 200, 500, 1000]
    rows = []
    print(f"{'parcels':>8} {'nodes':>6} {'cap':>5} {'sort(ms)':>9} {'knap(ms)':>9} "
          f"{'dijk(ms)':>9} {'tsp(ms)':>8} {'stops':>6} {'route km':>9}")
    for n in sizes:
        nodes = max(20, n // 2)
        cap = n * 2                       # capacity grows with input
        adj = generate_graph(nodes, seed=n)
        parcels = generate_parcels(n, nodes, seed=n + 1)
        res = plan_trip(adj, parcels, cap)

        # correctness checks
        assert [(p.deadline, -p.value) for p in res["sorted"]] == \
               sorted((p.deadline, -p.value) for p in parcels), "sort wrong"
        assert sum(p.weight for p in res["chosen"]) <= cap, "overweight"
        assert sorted(res["route"][:-1]) == res["stops"] and res["route"][0] == res["route"][-1]

        ts = res["times"]
        rows.append((n, ts, len(res["stops"]), res["length"]))
        print(f"{n:>8} {nodes:>6} {cap:>5} {ts['sort']*1e3:>9.3f} {ts['knapsack']*1e3:>9.3f} "
              f"{ts['dijkstra']*1e3:>9.3f} {ts['tsp']*1e3:>8.3f} {len(res['stops']):>6} {res['length']:>9}")
    print("All correctness checks passed.")

    # merge sort vs insertion sort
    print("\nMerge sort vs insertion sort (ms):")
    cmp_sizes, ms, ins = [100, 500, 1000, 2000], [], []
    for n in cmp_sizes:
        ps = generate_parcels(n, 50, seed=n)
        k = lambda p: (p.deadline, -p.value)
        c = time.perf_counter(); merge_sort(ps, k); ms.append((time.perf_counter() - c) * 1e3)
        c = time.perf_counter(); insertion_sort(ps, k); ins.append((time.perf_counter() - c) * 1e3)
        print(f"  n={n:>5}: merge={ms[-1]:8.3f}  insertion={ins[-1]:9.3f}")

    # nearest-neighbor quality vs optimal on small instances
    print("\nNearest-Neighbor vs optimal (8 stops, 5 random graphs):")
    ratios = []
    for seed in range(5):
        adj = generate_graph(30, seed=100 + seed)
        stops = [DEPOT] + random.Random(seed).sample(range(1, 30), 7)
        dist, _ = distance_matrix(adj, stops)
        _, nn = nearest_neighbor_route(dist, stops)
        _, opt = brute_force_route(dist, stops)
        ratios.append(nn / opt)
        print(f"  graph {seed}: NN={nn}, optimal={opt}, ratio={nn/opt:.3f}")
    print(f"  average ratio = {sum(ratios)/len(ratios):.3f}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
        xs = [r[0] for r in rows]
        for step in ["sort", "knapsack", "dijkstra", "tsp"]:
            ax[0].plot(xs, [r[1][step] * 1e3 for r in rows], marker="o", label=step)
        ax[0].set_xlabel("Number of parcels"); ax[0].set_ylabel("Runtime (ms)")
        ax[0].set_title("Runtime of each pipeline step"); ax[0].legend(); ax[0].grid(alpha=.3)
        ax[1].plot(cmp_sizes, ms, marker="o", label="Merge sort O(n log n)")
        ax[1].plot(cmp_sizes, ins, marker="s", label="Insertion sort O(n^2)")
        ax[1].set_xlabel("Number of parcels"); ax[1].set_ylabel("Runtime (ms)")
        ax[1].set_title("Sorting comparison"); ax[1].legend(); ax[1].grid(alpha=.3)
        plt.tight_layout(); plt.savefig("runtime_chart.png", dpi=150)
        print("\nSaved runtime_chart.png")
    except ImportError:
        print("\nmatplotlib not installed: pip install matplotlib to get the chart")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("demo", "all"):
        demo()
    if mode in ("benchmark", "all"):
        benchmark()
