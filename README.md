# Mini-Courier Planner (DAA Capstone, ETCCDA302)

An integrated Python prototype that, given parcels and a city road graph, produces a prioritized parcel order, an optimal packing plan for one trip, and a delivery route.

## Execution steps

```
pip install matplotlib        # only needed for the runtime chart
python courier_planner.py demo        # small dataset, full trace
python courier_planner.py benchmark   # runtime tests + runtime_chart.png
python courier_planner.py all         # both
```

Outputs: `output_trace.txt` (console trace), `runtime_chart.png`, `sample_dataset.json`.

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
Parcels are sorted earliest-deadline-first, ties broken by higher priority. The knapsack maximizes total priority value within the weight limit; the DP table is printed and chosen parcels are recovered by backtracking.

Demo result: capacity 30 kg, selected parcels 8, 11, 12 with total value 287 and weight 28 kg.

## Phase 3: Graph and route
Dijkstra gives shortest paths from the depot to each stop. A distance matrix between all stops feeds Nearest-Neighbor TSP, which returns to the depot.

Demo result: route `[0, 7, 1, 8, 0]`, length 40 km. Brute force confirms the optimum is also 40 km (ratio 1.000).

## Phase 4: Performance testing

| Parcels | Nodes | Sort (ms) | Knapsack (ms) | Dijkstra (ms) | TSP (ms) |
|---|---|---|---|---|---|
| 10 | 20 | 0.011 | 0.018 | 0.059 | 0.006 |
| 100 | 50 | 0.110 | 1.812 | 1.020 | 0.033 |
| 500 | 250 | 0.773 | 54.908 | 29.154 | 0.733 |
| 1000 | 500 | 1.555 | 234.888 | 126.542 | 2.891 |

See `runtime_chart.png`. Times vary by machine.

**Observations**
- Knapsack dominates because the table has n*W cells and W grows with n; Dijkstra is second because it runs once per stop.
- Merge sort vs insertion sort at n=2000: about 3 ms vs 112 ms, confirming O(n log n) vs O(n^2).
- Nearest-Neighbor on 8-stop instances averaged 1.07x the optimal route length (worst 1.145).
- Correctness checks (asserted in the benchmark): sorted order is correct, capacity is never exceeded, route starts and ends at the depot and visits every stop once.

**Future optimizations**
- Knapsack: use a 1-D DP array (O(W) space), or scale/bucket weights.
- Dijkstra: run only between required stops, cache results, or use A* for single pairs.
- Route quality: apply 2-opt improvement after Nearest-Neighbor, or use Christofides (1.5-approximation).
- Honor deadlines inside the route (time windows) and split parcels across multiple trips.

## Phase 5: Notes for demonstration
- Be ready to trace the knapsack table and Dijkstra on the demo graph.
- Know why Nearest-Neighbor is not optimal: it never looks ahead and the last leg back to the depot can be long.
- Add your own screenshots of the terminal output and `runtime_chart.png` to the submission.
# DAA_Capstone_project
