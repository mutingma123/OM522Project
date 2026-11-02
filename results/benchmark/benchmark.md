# Optimality benchmark

The positional mixed-integer program (see src/pfsp/mip.py) solved with HiGHS 1.15.1, one thread, a relative gap tolerance of 0, and a 600 s limit, on Intel(R) Core(TM) Ultra 7 155U. The solver's job order is re-timed by the execution rule and the independent checker confirms it and supplies the measures. The other columns repeat the two methods' results with their default settings.

| Instance | Jobs | Solver status | Optimal TWT | Dual bound | Seconds | Nodes | Waiting of the solver's order | EDD rule TWT | Iterated greedy TWT | Iterated greedy waiting |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hand_checkable | 6 | Optimal | 233 | 233.000 | 0.4 | 60 | 37 | 281 | 233 | 37 |
| development_small | 15 | Optimal | 21 | 21.000 | 85.8 | 15403 | 323 | 1417 | 21 | 252 |
