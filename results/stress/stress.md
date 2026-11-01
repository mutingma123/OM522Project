# Stress test of the fixed plans

Instance development_medium. Each processing time is multiplied by an independent lognormal factor with mean 1 and coefficient of variation 0.2. 30 scenarios come from seed 20261103 and are saved in scenarios/ before either method runs. Each plan keeps its sequence and starts every operation as early as the realized times allow. The independent checker confirms every realized schedule against its scenario. The 90th percentile uses linear interpolation.

| Method | Planned TWT | Mean TWT | 90th percentile TWT | Planned waiting | Mean waiting | 90th percentile waiting | Scenarios breaking a hard constraint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EDD rule | 2,371.0 | 3,541.1 | 4,616.6 | 2,040.0 | 2,454.5 | 2,768.6 | 0 |
| Iterated greedy | 58.0 | 420.6 | 592.2 | 794.0 | 1,276.9 | 1,454.9 | 0 |

Iterated greedy has the lower weighted tardiness in 30 of 30 scenarios.

## Sweep over variability

| Coefficient of variation | Seed | Rule mean TWT | Rule 90th percentile | Iterated greedy mean TWT | Iterated greedy 90th percentile | Scenarios where iterated greedy is better |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.1 | 6522 | 2,720.1 | 3,171.6 | 148.1 | 228.4 | 30 of 30 |
| 0.2 | 6523 | 3,273.5 | 4,425.0 | 407.2 | 643.9 | 30 of 30 |
| 0.3 | 6524 | 4,139.8 | 6,213.4 | 952.5 | 1,676.0 | 30 of 30 |
| 0.5 | 6525 | 6,680.4 | 9,498.8 | 2,996.7 | 5,434.2 | 30 of 30 |
| 0.8 | 6526 | 12,230.5 | 17,420.0 | 8,901.6 | 14,219.8 | 29 of 30 |
