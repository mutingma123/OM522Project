# Prototype video outline (at most 10 minutes)

The prototype rubric (guide Section 4.1) asks for a fresh instance, the rule reproducing the worked example, the checker confirming the rule on the worked example and one development instance, the researched method and its source, a first implementation compared with the rule, and every member's walk-through of an agent-drafted component. The timings below leave a minute of slack.

## Commands, in recording order

Copy a supplied instance to a new path first, so the video shows the tool reading input it has not seen at that path.

```bash
# macOS or Linux
cp -r data/development_medium ~/fresh_medium
# Windows PowerShell
Copy-Item -Recurse data/development_medium $HOME/fresh_medium

pixi run test                                                                    # 30 passed
pixi run solve data/hand_checkable out/hand_rule --method rule                   # TWT 281, waiting 13
pixi run check data/hand_checkable out/hand_rule/decision.json --expect data/worked-example/metrics.json
pixi run solve ~/fresh_medium out/medium_rule --method rule                      # TWT 2371
pixi run check ~/fresh_medium out/medium_rule/decision.json                      # FEASIBLE
pixi run solve ~/fresh_medium out/medium_ig                                      # TWT 58, about 3 s
pixi run check ~/fresh_medium out/medium_ig/decision.json                        # FEASIBLE
pixi run solve data/edge_case out/edge                                           # rejected, exit 1
```

## Timeline

| Time | Segment | What to show and say |
| --- | --- | --- |
| 0:00 to 1:00 | The decision | The README's opening paragraph in your own words: one sequence for all eight stages, weighted tardiness as the primary measure, waiting as the secondary one. |
| 1:00 to 3:00 | Rule to beat and test 1 | Run `pixi run test`. Trace the first two jobs of the EDD sequence on the hand-checkable case by hand (J001 starts S1 at its release 13, J002 waits for S1 until 24). Run the rule and the checker with `--expect`; every measure matches `metrics.json`. |
| 3:00 to 4:00 | Checker on a development instance | Solve the fresh copy with the rule and check it. Mention that the checker imports nothing from the solver. Show the edge case rejection message. |
| 4:00 to 6:30 | Researched method | Iterated greedy with local search, Ruiz and Stützle (2008, EJOR). Representation: a permutation. Build: NEH_EWDD (ascending $d_j / w_j$, best-position insertion). Improve: remove 4 random jobs, reinsert greedily, insertion local search, constant-temperature acceptance. Stop: 5000 iterations, seed 522. Why it should beat EDD: EDD ignores weights, releases, and processing times, while every step here compares actual weighted tardiness over eight stages; the source reports it as the best of the methods tested for weighted tardiness. |
| 6:30 to 8:00 | First implementation against the rule | Solve the fresh copy with the default command and check it. Medium: TWT 58 against 2,371, waiting 794 against 2,040. Name one limit honestly: on the six-job case it reaches the optimum (233 against 281) but has more waiting (37 against 13). |
| 8:00 to 10:00 | Walk-throughs | Each member: one agent-drafted component, one thing that was wrong or unclear, how it was checked. Candidates below. |

## Walk-through candidates

Each candidate below actually happened during development. Each member takes a different one, and the final video needs a different one again.

| Component | What was wrong or unclear in the agent's version | How it was checked |
| --- | --- | --- |
| `src/pfsp_check/check.py` (checker) | Violation messages printed every time as a float, such as `starts at 23.0`, which does not match how the data are written and made test expectations fragile. | `tests/test_checker.py` damages the worked example in six ways and asserts each message; fixed in commit `9db7864`. |
| `src/pfsp/ig.py` (researched method) | The first plan ordered NEH by plain EDD and used the 2007 makespan setting $T = 0.4$. Reading Ruiz and Stützle (2008) changed it to the weighted order $d_j / w_j$ (NEH_EWDD) and $T = 0.5$. | `tests/test_ig.py`: enumerating all 720 sequences of the hand-checkable case shows the method reaches the optimum, and its decisions pass the checker and beat the rule on all four instances. |
| `src/pfsp/timing.py` (`best_insertion`) | The kernel stops evaluating a candidate position early. It was unclear whether that shortcut could skip the true best position. | It is valid because tardiness and waiting only grow as jobs are appended; `test_best_insertion_matches_brute_force` compares it with evaluating every position on 20 random cases. |
| Paper retrieval for the method | The library tool returned Campbell, Dudek, and Smith (1970) when asked for the NEH (1983) DOI, and a second attempt returned an unrelated 2025 paper. | Reading the first page exposed the mismatch; the files were removed and `library/LEDGER.md` records it. The README takes the NEH steps from Ruiz and Stützle (2007). |
| `src/pfsp/compare.py` (comparison plot) | The first plot clipped the right panel's title and drew NEH_EWDD on top of iterated greedy where both reach the optimum, hiding the researched method. | Viewing the rendered PNG; the method is now drawn last and the legend sits below both panels. |
