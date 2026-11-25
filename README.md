# Mini-Courier Planner

**DAA Capstone Assignment (ETCCDA302), K.R. Mangalam University, Gurugram**

| | |
|---|---|
| **Student** | Dev Kaushik |
| **Roll Number** | 2501730247 |
| **Programme** | B.Tech CSE (AI & ML), Section B |
| **Faculty** | Ankita Gupta |
| **Language** | Python 3 |

An integrated Python prototype that, given parcels and a city road graph, produces a prioritized parcel order, an optimal packing plan for one trip, and a delivery route. It combines merge sort, 0/1 knapsack dynamic programming, Dijkstra's algorithm and nearest-neighbor TSP approximation, and measures the runtime of each step.

## Repository contents

| File / folder | Purpose |
|---|---|
| `courier_planner.py` | Complete source code (all algorithms, demo and benchmark) |
| `sample_dataset.json` | Sample dataset (graph, parcels, capacity) saved by the demo |
| `output_trace.txt` | Console output trace of a full run |
| `runtime_chart.png` | Runtime chart of all pipeline steps and sort comparison |
| `screenshots/` | Terminal output screenshots |
| `Mini-Courier-Planner-Report.pdf` | Final project report |

## Execution steps

```
pip install matplotlib                 # only needed for the runtime chart
python3 courier_planner.py demo        # small dataset, full trace
python3 courier_planner.py benchmark   # runtime tests + runtime_chart.png
python3 courier_planner.py all         # both
```

Running `demo` also writes `sample_dataset.json`; running `benchmark` writes `runtime_chart.png`.

## Phase 1: Design

**Data design**
- `Parcel(pid, dest, weight, value, deadline)`: `dest` is a node in the city graph, `weight` in kg (integer), `value` is priority 1-100, `deadline` in hours.
- Graph: weighted undirected adjacency list `{node: [(neighbor, km), ...]}`. Node 0 is the depot.
- Datasets are generated with fixed random seeds so results are reproducible.

**Pipeline**

```
Parcels --> Merge Sort (deadline, priority) --> 0/1 Knapsack DP (truck capacity)
        --> chosen parcels --> unique delivery stops
        --> Dijkstra from each stop (distance matrix)
        --> Nearest-Neighbor TSP --> final route + length
```

| Step | Algorithm | Why chosen | Complexity |
|---|---|---|---|
| Prioritize | Merge Sort | Stable, guaranteed O(n log n) | O(n log n) time, O(n) space |
| Pack | 0/1 Knapsack DP | A parcel is taken whole or not at all; greedy is not optimal | O(n*W) time and space |
| Shortest paths | Dijkstra (min-heap) | Non-negative road lengths | O((V+E) log V) per source |
| Route | Nearest-Neighbor TSP | TSP is NP-hard; greedy gives a fast approximation | O(k^2) |

## Phase 2: Sorting and packing

Parcels are sorted earliest-deadline-first, ties broken by higher priority. The knapsack maximizes total priority value within the weight limit; the DP table is printed and the chosen parcels are recovered by backtracking.

**Demo result:** capacity 30 kg, selected parcels 8, 11 and 12 with total priority value 287 and total weight 28 kg.

## Phase 3: Graph and route

Dijkstra gives shortest paths from the depot to each stop. A distance matrix between all stops feeds Nearest-Neighbor TSP, which returns to the depot.

**Demo result:** route `[0, 7, 1, 8, 0]`, length 40 km. Brute force confirms the optimum is also 40 km (approximation ratio 1.000).

## Phase 4: Performance testing

Runtimes in milliseconds:

| Parcels | Nodes | Capacity | Sort | Knapsack | Dijkstra | TSP | Stops | Route km |
|---|---|---|---|---|---|---|---|---|
| 10 | 20 | 20 | 0.035 | 0.055 | 0.215 | 0.019 | 5 | 69 |
| 50 | 25 | 100 | 0.135 | 0.899 | 0.692 | 0.045 | 16 | 184 |
| 100 | 50 | 200 | 0.219 | 5.576 | 3.226 | 0.121 | 30 | 328 |
| 200 | 100 | 400 | 1.066 | 16.500 | 8.539 | 0.246 | 61 | 604 |
| 500 | 250 | 1000 | 1.793 | 158.170 | 130.964 | 5.018 | 145 | 1474 |
| 1000 | 500 | 2000 | 6.302 | 535.916 | 268.340 | 5.273 | 280 | 2544 |

See `runtime_chart.png`. Exact times vary by machine; the growth trend is what matters.

**Correctness checks** (asserted in the benchmark): sorted order is correct, capacity is never exceeded, and the route starts and ends at the depot and visits every stop once. All checks passed.

**Observations**
- Knapsack dominates because the table has n*W cells and W grows with n; Dijkstra is second because it runs once per stop.
- Sorting and TSP stay fast even at 1000 parcels / 280 stops.
- Merge sort vs insertion sort at n = 2000: about 8.9 ms vs 245.5 ms, confirming O(n log n) vs O(n^2).
- Nearest-Neighbor on 8-stop instances averaged 1.07x the optimal route length (worst case 1.145).

**Future optimizations**
- Knapsack: use a 1-D DP array (O(W) space), or scale/bucket weights to shrink W.
- Dijkstra: run only between required stops, cache results, or use A* for single pairs.
- Route quality: apply 2-opt improvement after Nearest-Neighbor, or use Christofides (1.5-approximation).
- Honor deadlines inside the route (time windows) and split parcels across multiple trips.

## Phase 5: Results and demonstration

- Screenshots of the terminal output are in the `screenshots/` folder.
- Full explanation of results, tables and figures is in `Mini-Courier-Planner-Report.pdf`.
- Nearest-Neighbor is not optimal because it never looks ahead and the last leg back to the depot can be long; the 8-stop tests above quantify this.
