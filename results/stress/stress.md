# Stress test of the fixed plans

Instance development_medium. Each processing time is multiplied by an independent lognormal factor with mean 1 and coefficient of variation 0.2. 30 scenarios come from seed 20261103 and are saved in scenarios/ before either method runs. Each plan keeps its sequence and starts every operation as early as the realized times allow. The independent checker confirms every realized schedule against its scenario. The 90th percentile uses linear interpolation.

| Method | Planned TWT | Mean TWT | 90th percentile TWT | Planned waiting | Mean waiting | 90th percentile waiting | Scenarios breaking a hard constraint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EDD rule | 2,371.0 | 3,541.1 | 4,616.6 | 2,040.0 | 2,454.5 | 2,768.6 | 0 |
| Iterated greedy | 58.0 | 420.6 | 592.2 | 794.0 | 1,276.9 | 1,454.9 | 0 |

| Method | Late jobs in the plan | Mean late jobs across scenarios | On-time jobs in the plan | Median slack of on-time jobs | Median simulated completion standard deviation | Median mean completion delay | On-time jobs with slack below that standard deviation | On-time jobs late in some scenario | Mean late probability of an on-time job | On-time jobs made late per scenario |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EDD rule | 34 | 36.1 | 11 | 28.0 | 9.9 | 3.5 | 4 | 6 | 0.279 | 3.07 |
| Iterated greedy | 4 | 11.5 | 41 | 31.0 | 8.3 | 9.3 | 6 | 20 | 0.185 | 7.57 |

Iterated greedy has the lower weighted tardiness in 30 of 30 scenarios; the mean per-scenario reduction is 3,120.5 weighted minutes with a standard error of 150.1; its 10th percentile is 2,235.1 and its smallest value 1,948.6.

## Sweep over variability

| Coefficient of variation | Seed | Rule mean TWT | Rule 90th percentile | Iterated greedy mean TWT | Iterated greedy 90th percentile | Mean reduction (standard error) | 10th percentile of the reduction | Smallest reduction | Scenarios where iterated greedy is better |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.1 | 6522 | 2,720.1 | 3,171.6 | 148.1 | 228.4 | 2,572.0 (65.9) | 2,048.3 | 1,858.4 | 30 of 30 |
| 0.2 | 6523 | 3,273.5 | 4,425.0 | 407.2 | 643.9 | 2,866.4 (121.3) | 2,055.3 | 1,821.3 | 30 of 30 |
| 0.3 | 6524 | 4,139.8 | 6,213.4 | 952.5 | 1,676.0 | 3,187.3 (203.8) | 1,781.1 | 823.3 | 30 of 30 |
| 0.5 | 6525 | 6,680.4 | 9,498.8 | 2,996.7 | 5,434.2 | 3,683.7 (223.8) | 2,473.2 | 1,405.8 | 30 of 30 |
| 0.8 | 6526 | 12,230.5 | 17,420.0 | 8,901.6 | 14,219.8 | 3,329.0 (342.7) | 851.5 | -870.4 | 29 of 30 |
