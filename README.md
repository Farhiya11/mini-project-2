# Simulator Engine
Simulator Engine for 02225 DRTS Mini-project 2.

The simulator evaluates periodic TSN streams in a simplified Credit-Based Shaper (CBS) setup. It reads the generated/provided `topology.json`, `streams.json`, and `routes.json` files, simulates frame transmission through the network, and reports observed end-to-end response times. When a `WCRTs.csv` file is available, the simulator also compares the observed response times against the analytical worst-case response times.


## Files
- `src/models.py`: data classes and unit conventions.
- `src/routing.py`: converts `routes.json` egress-port paths into directed topology links.
- `src/cbs.py`: one output-port Credit-Based Shaper.
- `src/events.py`: deterministic event queue.
- `src/engine.py`: periodic frame generation, store-and-forward forwarding, end-to-end measurements.
- `src/io.py`: JSON and CSV parsing/writing.
- `src/reports.py`: WCRT comparison columns.
- `src/cli.py`: command-line interface.
- `run_simulator.py`: convenience entry point.


## Simulator Engine Project Structure
The simulator is organized as a small Python package plus one top-level runner script.

```text
mini-project-2/
├── run_simulator.py
├── README.md
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── models.py
│   ├── io.py
│   ├── routing.py
│   ├── cbs.py
│   ├── events.py
│   ├── engine.py
│   └── reports.py
├── test_cases/
│   ├── generated/
│   │   ├── baseline/
│   │   │   ├── test_case_1/
│   │   │   ├── test_case_2/
│   │   │   └── test_case_3/
│   │   └── heavy/
│   │   │   └── test_case_1/
│   │   │   ├── test_case_2/
│   │   │   └── test_case_3/
│   └── provided/
│       ├── test_case_1/
│       │   ├── README.txt
│       │   ├── topology.json
│       │   ├── streams.json
│       │   ├── routes.json
│       │   └── WCRTs.csv
│       ├── test_case_2/
│       └── test_case_3/
└── results/
    ├── baseline/
    │   ├── test_case_1_results.csv
    │   └── test_case_1_ports.csv
    └── heavy/
        ├── test_case_1_results.csv
        └── test_case_1_ports.csv
```


## Assumptions and important conventions
1. `size` is in bytes. Link bandwidth is in Mbps, which equals bits per microsecond. The transmission time is: 
$$ C\_us = (size\_bytes * 8) / bandwidth\_mbps $$


2. Per-link `bandwidth_mbps` overrides are supported. If a link omits `bandwidth_mbps`, the simulator uses topology-level `default_bandwidth_mbps`. You may intentionally force a single bandwidth with `--force-bandwidth-mbps`.

3. `routes.json` hops are interpreted as egress ports. A hop `{ "node": "SW1", "port": 6 }` means the frame leaves `SW1` via port 6. The simulator cross-checks that this egress port leads to the next hop node in `topology.json`.

4. The source end system is included as a real hop. A path `ES -> SW -> ES` therefore has two output ports and two serialization terms.

5. Streams are unidirectional. Interference happens per output port. Opposite directions use different directed links/egress ports and therefore do not interfere unless they share an egress port in another topology.

6. PCP mapping is fixed for the reference tests:
   - PCP 2 = Class A, highest AVB priority.
   - PCP 1 = Class B.
   - PCP 0 = Best Effort.

7. The simulator measures response time from frame release at the source until full reception at the destination.

8. Default slopes are the reference equal-magnitude slopes: `idleSlope = +0.5 * portRate` and `sendSlope = -0.5 * portRate` for both AVB classes. This is configured with `--idle-slope-fraction 0.5`. The implementation computes `sendSlope = idleSlope - portRate`, so 0.5 gives the required +0.5C/-0.5C behavior.

9. The validity condition `sum(idleSlope fractions for AVB classes) <= 1` is checked. With the default two AVB classes at 0.5 each, the system is exactly at the boundary and BE has no analytical WCRT guarantee.

10. CBS credit mechanics are simulated explicitly:
    - AVB queues transmit only when credit is non-negative.
    - Credit decreases at `sendSlope` during that class's own transmission.
    - Credit increases at `idleSlope` while the class is backlogged but not transmitting.
    - Negative credit recovers toward zero.
    - Positive credit is reset to zero when the queue is idle.

11. By default, all streams release together at `t=0` and then periodically. If `--sim-time` is omitted, the simulator runs for several hyperperiods (`--hyperperiods 5` by default), which is more meaningful than an arbitrary short fixed horizon.


## Example
From a folder containing `topology.json`, `streams.json`, `routes.json`, and optionally `WCRTs.csv`:

```bash
python3 run_simulator.py --topology topology.json --streams streams.json --routes routes.json --wcrt WCRTs.csv --hyperperiods 10 --out simulation_results.csv --ports-out port_results.csv
```

To intentionally use the simplified assumption of one uniform 100 Mbps rate on every link:

```bash
python3 run_simulator.py --topology topology.json --streams streams.json --routes routes.json --wcrt WCRTs.csv --force-bandwidth-mbps 100
```


## Test cases and evaluation
This project uses three categories of test cases:

1. **Provided test cases**
2. **Baseline generated test cases**
3. **Heavy generated test cases**

The provided cases are used for validation against analytical WCRT values. The generated baseline and heavy cases are used to test that the simulator works on additional inputs and to observe how the response times change when the workload becomes heavier.


### Provided test cases
The provided test cases are stored in:

```text
test_cases/provided/
```

The most important one is:

```text
test_cases/provided/test_case_1/
```

This folder contains:

```text
README.txt
topology.json
streams.json
routes.json
WCRTs.csv
```

The `WCRTs.csv` file contains analytical worst-case response times for the AVB streams. Therefore, the provided case is the main validation case. The expected check is:

```text
observed maximum response time <= analytical WCRT
```

Run command for the provided test case:

```bash
python3 run_simulator.py \
  --topology test_cases/provided/test_case_1/topology.json \
  --streams test_cases/provided/test_case_1/streams.json \
  --routes test_cases/provided/test_case_1/routes.json \
  --wcrt test_cases/provided/test_case_1/WCRTs.csv \
  --hyperperiods 100 \
  --out results/provided_test_case_1_results.csv \
  --ports-out results/provided_test_case_1_ports.csv
```

The provided case is used for analytical validation. If all AVB streams have `observed_leq_wcrt = True`, then the simulation results are consistent with the analytical WCRT bounds.


### Baseline generated test cases
The baseline generated test cases are stored in:

```text
test_cases/generated/baseline/
```

These cases were generated using the original `examples/small_tests_config.json` from the TSN test-case generator.

The baseline configuration keeps the original small setup:

- 2 switches.
- 2 end systems.
- PCP 2 streams for Class A.
- PCP 1 streams for Class B.
- PCP 0 streams for Best Effort.
- Packet sizes between 500 and 1500 bytes.
- Periods selected from 1000 µs and 2000 µs.
- Shortest-path routing.

Run command for baseline generated test case 1:

```bash
python3 run_simulator.py \
  --topology test_cases/generated/baseline/test_case_1/topology.json \
  --streams test_cases/generated/baseline/test_case_1/streams.json \
  --routes test_cases/generated/baseline/test_case_1/routes.json \
  --hyperperiods 50 \
  --out results/baseline/test_case_1_results.csv \
  --ports-out results/baseline/test_case_1_ports.csv
```

The baseline generated case does not contain `WCRTs.csv`, so it is not used for analytical WCRT validation. It is used as a robustness check to show that the simulator works on generated input files and is not hardcoded to the provided example.


### Heavy generated test case
The heavy generated test case is stored in:

```text
test_cases/generated/heavy/test_case_1/
```

It is based on the same generator setup as the baseline case, but the traffic load was increased.

The heavy configuration changes were:

- Class A stream count increased from 2 to 3.
- Class B stream count increased from 2 to 3.
- Best Effort stream count kept unchanged.
- Minimum packet size increased from 500 bytes to 1000 bytes.
- Maximum packet size kept at 1500 bytes.

These changes increase the amount of AVB traffic and increase the transmission time of many frames. This should make queueing effects more visible and can increase observed response times compared with the baseline generated case.

Run command for heavy generated test case 1:

```bash
python3 run_simulator.py \
  --topology test_cases/generated/heavy/test_case_1/topology.json \
  --streams test_cases/generated/heavy/test_case_1/streams.json \
  --routes test_cases/generated/heavy/test_case_1/routes.json \
  --hyperperiods 50 \
  --out results/heavy/test_case_1_results.csv \
  --ports-out results/heavy/test_case_1_ports.csv
```

The heavy generated case also does not contain `WCRTs.csv`, so it is not used for analytical WCRT validation. It is used as a stress test.


### Interpreting result files
The simulator produces two result files per run.


#### Stream result file
Example:

```text
results/baseline/test_case_1_results.csv
results/heavy/test_case_1_results.csv
```

Important columns:

- `stream_id`: stream identifier.
- `class`: mapped traffic class, for example A, B, or BE.
- `frames_observed`: number of completed frames observed.
- `max_rt_us`: maximum observed end-to-end response time in microseconds.
- `deadline_us`: stream deadline.
- `deadline_misses`: number of frames whose response time exceeded the deadline.
- `analytical_wcrt_us`: analytical WCRT, only available when `WCRTs.csv` is provided.
- `observed_leq_wcrt`: whether the observed maximum response time is below the analytical WCRT.


#### Port result file
Example:

```text
results/baseline/test_case_1_ports.csv
results/heavy/test_case_1_ports.csv
```

Important columns:

- `port`: output port identifier.
- `utilization_busy_fraction`: fraction of simulation time where the port was transmitting.
- `tx_pcp2`: number of transmitted Class A frames.
- `tx_pcp1`: number of transmitted Class B frames.
- `tx_pcp0`: number of transmitted Best Effort frames.
- `max_q_pcp2`: maximum observed Class A queue length.
- `max_q_pcp1`: maximum observed Class B queue length.
- `max_q_pcp0`: maximum observed Best Effort queue length.

Higher port utilization and larger maximum queue lengths usually indicate more interference and higher response times.


### Summary of test purpose
| Case | Folder | Has `WCRTs.csv`? | Purpose |
|---|---|---:|---|
| Provided | `test_cases/provided/test_case_1/` | Yes | Validate simulation results against analytical WCRT bounds |
| Baseline generated | `test_cases/generated/baseline/test_case_1/` | No | Check that the simulator works on generated inputs |
| Heavy generated | `test_cases/generated/heavy/test_case_1/` | No | Stress the simulator with more AVB traffic and larger frames |

The provided case is the correctness/validation case. The baseline generated case is a robustness case. The heavy generated case is a stress case.