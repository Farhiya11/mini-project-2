# WCRT Analytical Tool
This tool computes analytical Worst-Case Response Times (WCRTs) for AVB streams in the TSN/CBS mini-project-2 for the Distributed Real-Time Systems course at DTU.

It is the analytical counterpart to the simulator engine. The simulator produces observed response times from a discrete-event simulation, while this tool computes analytical WCRT bounds from the same test-case input files.

## Purpose
The purpose of this tool is to:

- read TSN test cases from JSON files;
- compute analytical WCRT values for AVB streams;
- check whether each computed WCRT is below the stream deadline;
- provide values that can be compared with the simulator's observed maximum response times.

The final validation step is:

```text
simulated maximum response time <= analytical WCRT
```

This comparison should be made for AVB streams only.

## Input files
Each test case must contain:

```text
topology.json
streams.json
routes.json
```

### `topology.json`
Defines the network topology:

- switches;
- end systems;
- links;
- link source and destination nodes;
- port numbers;
- link bandwidths;
- propagation delays.

The analytical tool uses the link bandwidth to compute the transmission time of each frame on each link.

### `streams.json`
Defines the traffic streams:

- stream ID;
- stream name;
- source end system;
- destination end system;
- PCP priority;
- frame size;
- period;
- deadline.

The tool uses the stream size, PCP, and deadline.

### `routes.json`
Defines the path followed by each stream.

The tool converts each route into the set of directed links traversed by the stream. The WCRT of a stream is then computed by summing the per-link delay contributions along the route.

## Traffic classes
The project uses the following priority mapping:

```text
PCP 2 = AVB Class A
PCP 1 = AVB Class B
PCP 0 = Best Effort
```

The analytical WCRT comparison should focus on AVB streams:

```text
Class A: PCP 2
Class B: PCP 1
```

Best Effort streams may be present in the input and may be printed by the tool, but BE traffic does not provide real-time guarantees. Therefore, BE results should not be interpreted as guaranteed analytical WCRTs in the report.

## Transmission time
For each stream on each link, the transmission time is computed as:

```text
C_i = size_bytes * 8 / bandwidth_mbps
```

Because:

```text
1 Mbps = 1 bit per microsecond
```

the result is directly expressed in microseconds.

If a link defines `bandwidth_mbps`, that value is used. Otherwise, the topology-level `default_bandwidth_mbps` is used.

## WCRT computation
The main computation is implemented in:

```text
src/analysis.py
```

The main function is:

```python
compute_wcrt(streams, topology, routes, idle_slope=0.5)
```

For each stream, the tool:

1. reads the stream route;
2. maps the route to the directed links used by the stream;
3. finds all other streams that share each link;
4. computes the stream transmission time on that link;
5. computes a per-link worst-case delay contribution;
6. sums the contributions over the full path;
7. returns the end-to-end WCRT.

The WCRT of a stream is computed compositionally:

```text
WCRT(stream) = sum of WCD contributions over all links in the route
```

If multiple redundant paths are present, the implementation takes the maximum WCRT among the paths.

## Interference terms
For each stream `i` on each link, the tool considers three interference components.

### Same-Priority Interference
Same-priority interference accounts for other streams on the same link with the same PCP:

```text
SPI_i = sum(C_j / idle_slope)
```

for all streams `j` on the same link such that:

```text
PCP_j = PCP_i
j != i
```

### Lower-Priority Interference
Lower-priority interference accounts for non-preemptive blocking by a lower-priority frame already in transmission:

```text
LPI_i = max(C_k)
```

for all streams `k` on the same link such that:

```text
PCP_k < PCP_i
```

If no lower-priority stream is present, this term is zero.

### Higher-Priority Interference
For Class A, there is no higher-priority AVB traffic in this project model:

```text
HPI_i = 0
```

For Class B, the implementation accounts for interference from the highest-priority AVB class on the link:

```text
HPI_i = LPI_i + max(C_A)
```

where `max(C_A)` is the maximum transmission time of a Class A stream on the same link.

## Per-link WCD formulas
For the highest AVB class on a link:

```text
WCD_i = C_i + SPI_i + LPI_i
```

For lower AVB classes:

```text
WCD_i = C_i + SPI_i + LPI_i + HPI_i
```

The end-to-end WCRT is the sum of these per-link WCD values across the route.

## Output
The current tool prints a table to the terminal.

Example:

```bash
Case                              ID      Name      PCP     Deadline    WCRT (us) 
----------------------------------------------------------------------------------
generated/baseline/test_case_1    0       Stream0   2       1000        764.90      OK
generated/baseline/test_case_1    1       Stream1   2       1000        764.90      OK
generated/baseline/test_case_1    2       Stream2   2       1000        728.45      OK
generated/baseline/test_case_1    3       Stream3   2       1000        728.45      OK
generated/baseline/test_case_1    4       Stream4   1       1000        1057.39     MISS
...
```

Each row contains:

- stream ID;
- stream name;
- PCP priority;
- deadline;
- computed WCRT in microseconds;
- status:
  - `OK` if `WCRT <= deadline`;
  - `MISS` otherwise.

## File overview

```text
main.py
src/parser.py
src/analysis.py
README.md
```

### `main.py`

Entry point of the analytical tool.

It:

1. loads all test cases;
2. calls `compute_wcrt`;
3. prints the WCRT table;
4. checks whether each WCRT is below the stream deadline.

### `src/parser.py`

Loads test cases from disk.

It reads:

```text
streams.json
topology.json
routes.json
```

and returns the parsed data to `main.py`.

In the original version, the parser expects test cases under:

```text
examples/test_case_*
```

### `src/analysis.py`

Contains the analytical WCRT computation.

It:

- builds link maps from the topology;
- maps stream routes to links;
- identifies streams sharing each link;
- computes transmission times;
- computes interference terms;
- sums per-link WCDs into end-to-end WCRTs.

## How to run
From the analytical tool folder:

```bash
python3 main.py
```

To save the terminal output:

```bash
python3 main.py > wcrt_output.txt
```
The output is also saved in `results/wcrt_results.csv`

## Recommended usage with the simulator
Use the same test cases for both tools.

For each case:

1. Run the analytical tool and save the WCRT output.
2. Run the simulator and save the simulation output.
3. Compare AVB streams.


## Relation to the simulator
The analytical tool and simulator serve different purposes.

- **Analytical tool**: computes safe WCRT bounds under the implemented analysis assumptions

- **Simulator**: observes response times for the simulated release pattern and duration

Simulation alone cannot prove a worst-case guarantee, because it only explores the scenarios that are simulated. The analytical WCRT provides the bound, and the simulator is used to check that observed response times stay below that bound.