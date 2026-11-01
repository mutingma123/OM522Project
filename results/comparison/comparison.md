# Deterministic comparison

Computer: Intel(R) Core(TM) Ultra 7 155U, Linux 6.18.54.1-microsoft-standard-WSL2, Python 3.12.16. Iterated greedy runs 5000 iterations with seed 522 and a 300 s safety cap, which no run reached. The rule and NEH_EWDD have no time limit and no randomness. Feasibility and every measure are recomputed by the independent checker from the exported decision. Times are in minutes; weighted tardiness is in weighted minutes.

| Instance | Jobs | Method | Feasible | Total weighted tardiness | Total waiting | Makespan | On-time fraction | Seconds |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| hand_checkable | 6 | EDD rule | yes | 281 | 13 | 139 | 0.000 | 0.000 |
| hand_checkable | 6 | Iterated greedy | yes | 233 | 37 | 136 | 0.000 | 0.212 |
| hand_checkable | 6 | NEH_EWDD only | yes | 233 | 37 | 136 | 0.000 | 0.000 |
| hand_checkable | 6 | Optimum (enumeration, benchmark) | yes | 233 | 37 | 136 | 0.000 | 0.001 |
| development_small | 15 | EDD rule | yes | 1,417 | 732 | 417 | 0.333 | 0.000 |
| development_small | 15 | Iterated greedy | yes | 21 | 252 | 357 | 0.867 | 0.524 |
| development_small | 15 | NEH_EWDD only | yes | 70 | 291 | 368 | 0.733 | 0.000 |
| development_medium | 45 | EDD rule | yes | 2,371 | 2,040 | 781 | 0.244 | 0.000 |
| development_medium | 45 | Iterated greedy | yes | 58 | 794 | 751 | 0.911 | 3.217 |
| development_medium | 45 | NEH_EWDD only | yes | 360 | 1,068 | 751 | 0.778 | 0.000 |
| development_large | 120 | EDD rule | yes | 23,015 | 7,863 | 1,812 | 0.233 | 0.000 |
| development_large | 120 | Iterated greedy | yes | 4,383 | 3,005 | 1,804 | 0.642 | 37.244 |
| development_large | 120 | NEH_EWDD only | yes | 9,452 | 3,928 | 1,804 | 0.400 | 0.003 |

## Iterated greedy under other seeds

The same settings with seeds 1, 2, 3, 4, 5 show how much the result depends on the seed.

| Instance | Jobs | Default seed | Lowest | Median | Highest | EDD rule |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hand_checkable | 6 | 233 | 233 | 233 | 233 | 281 |
| development_small | 15 | 21 | 21 | 21 | 21 | 1,417 |
| development_medium | 45 | 58 | 58 | 58 | 58 | 2,371 |
| development_large | 120 | 4,383 | 4,159 | 4,231 | 4,306 | 23,015 |
