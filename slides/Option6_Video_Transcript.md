# Live transcript for the 10 to 15 minute video: The Value of a Wrong Plan

Read this script aloud while recording, together with `Option6_Prototype_Slides.pdf`. Don presents every slide except slide 20, which Amir presents. At a calm 110 words per minute, with the commands pasted, it takes about 12:00. It stays inside the 10 to 15 minute window from 10:22 at 130 words per minute to 14:20 at 90.

## How to use this script

- Read one line at a time, and pause briefly after each line.
- Pause a little longer when the slide changes.
- **Bold** words carry the stress.
- Say numbers the way they are spelled out in the script. The slides show the exact values.
- Lines marked *(optional)* can be skipped if you are running long.
- Lines that start with **Paste** are terminal commands. Copy each one from this file, paste it, and press Enter. Keep talking while it runs.
- It is fine to stop the recording between slides and start again.
- The time beside each slide heading is when that slide should end.

## Before you record

1. In the repository folder, run `pixi install` and then `pixi run test` once. The first run compiles the timing code, so the runs in the video start quickly.
2. Make the terminal prompt short, so no folder path of your computer appears on screen.
   - bash: `PS1='$ '`
   - zsh: `PROMPT='$ '`
   - PowerShell: `function prompt { '> ' }`
3. Make the terminal font large, and type `clear`.
4. Open the slides in full-screen mode next to the terminal.
5. All output goes to `out/video`. If you record a second time, change `video` to `video2` in every command.

## Pronunciation guide

| Word | Say it like |
| --- | --- |
| Stützle | **SHTOOTS**-leh |
| Ruiz | roo-**EES** |
| iterated | **IT**-uh-ray-tid |
| greedy | **GREE**-dee |
| tardiness | **TAR**-dee-nis |
| weighted | **WAY**-tid |
| sequence | **SEE**-kwens |
| scenario | suh-**NAIR**-ee-oh |
| coefficient | koh-uh-**FISH**-unt |
| variability | vair-ee-uh-**BIL**-uh-tee |
| optimum, optimal | **OP**-tuh-mum, **OP**-tuh-mul |
| percentile | pur-**SEN**-tile |
| Gantt (the chart) | **GANT** |
| HiGHS (the solver) | like the word "highs" |
| EDD | say the letters: "E, D, D" |

## Slide 1: title (end by 0:24)

**Don:**

- Hello. I am **Don Ma**, presenting with **Amir Ranjbar**. This is OM five twenty-two, option six.
- Our title is **The Value of a Wrong Plan**.
- If a plan uses processing times that turn out **wrong**, is it **still worth having**?

## Slide 2: the talk in six parts (end by 0:30)

- The talk has **six parts**, shown here.

## Slide 3: the decision (end by 1:21)

- A planner must choose the **order** of jobs on a line with **eight stages**.
- Jobs **cannot pass**, so **one sequence** holds at every stage.
- Our main measure is **total weighted tardiness**: how late the jobs are, times their importance.
- Our second measure is **waiting between stages**, in job-minutes.
- The rule to beat is **E, D, D**, earliest due date. It sorts jobs by due date only.
- It does not see weights, release dates, or later stages.
- A job that is **slow at a later stage** holds up **every job behind it**.

## Slide 4: what is known (end by 1:56)

- On **exact data**, iterated greedy was the **best method tested** for weighted tardiness.
- With **random** times, most studies look at the **makespan**, the finish time of the last job.
- Reviews warn that an optimized schedule can **lose its advantage** when variability is high.
- So we ask: for weighted tardiness, does a searched sequence **stay better** when we hold it fixed?

## Slide 5: the model (end by 2:26)

- Once we fix a sequence, every start time is **fixed too**.
- Each operation starts when the job and the stage are **both ready**.
- From those times we compute tardiness, **Z**, and waiting, **W**.
- A mixed-integer program defines the **true optimum**, and a solver called **HiGHS** certifies it on the two smallest instances.

## Slide 6: the rule to beat (end by 3:19)

- Here is the rule on a small case with six jobs.
- Job **one** starts at its release, minute **thirteen**.
- Job **two** must **wait** until **twenty-four**, because stage one is busy.
- Let me run the tests.

**Paste:** `pixi run test`

- All **thirty-one** pass. Now the rule.

**Paste:** `pixi run solve data/hand_checkable out/video/hand_rule --method rule`

- Weighted tardiness is **two hundred eighty-one**.

**Paste:** `pixi run check data/hand_checkable out/video/hand_rule/decision.json --expect data/worked-example/metrics.json`

- The checker confirms it, and **every measure matches** the worked example.

## Slide 7: the checker (end by 4:17)

- The checker is **separate code**. It reads only the input files and the decision.
- It checks every constraint, then **recomputes** every measure by itself.
- It names every job and stage that breaks a constraint.
- Now a **fresh** copy of the medium instance.

**Paste (macOS, Linux, or WSL):** `mkdir -p out/video && cp -r data/development_medium out/video/fresh_medium`

**Paste (PowerShell instead):** `New-Item -ItemType Directory -Force out/video; Copy-Item -Recurse data/development_medium out/video/fresh_medium`

**Paste:** `pixi run solve out/video/fresh_medium out/video/medium_rule --method rule`

**Paste:** `pixi run check out/video/fresh_medium out/video/medium_rule/decision.json`

- **Feasible**, with weighted tardiness **two thousand three hundred seventy-one**.
- The **edge case** has a processing time of **zero**.

**Paste:** `pixi run solve data/edge_case out/video/edge`

- The tool **rejects** it and names the **file**, the **column**, and the **line**.

## Slide 8: the researched method (end by 4:51)

- Our method is **iterated greedy**, by **Ruiz** and **Stützle**.
- They built it for flow shops with setup times, so we set every setup time to **zero**.
- It compares sequences by their **real weighted tardiness** on all eight stages.
- So a **heavy** job can move ahead of a **light** one.
- Neither source has release dates, and our timing includes them.

## Slide 9: how it works (end by 5:36)

- **Step one**: order the jobs by **due date divided by weight**, and insert each at its **best position**.
- **Step two**: take each job out and put it back at its best position, until **nothing improves**.
- Then **repeat**: remove **four jobs** at random, put them back, and search again.
- *(optional)* Sometimes we accept a worse sequence, so the search does not get stuck.
- We **stop** after **five thousand** iterations, with a fixed seed, so a rerun gives the **same answer**.

## Slide 10: the experiment (end by 6:15)

- We test **four instances**, with six to one hundred twenty jobs.
- For the stress test, we take the forty-five-job instance and multiply each planned time by a **random factor** with mean one.
- So every planned time **is wrong**.
- We use **one hundred eighty** paired scenarios, at five levels of variability.
- We saved the scenarios **before** running either method, so both sequences face the same times.
- Both sequences stay **fixed**.

## Slide 11: the six-job result (end by 6:48)

- On the six-job case, the darker bars are heavier jobs.
- E, D, D puts job **five**, with weight **one**, before two jobs with weight **four**.
- Iterated greedy moves job five to the **end**.
- Tardiness falls from **two hundred eighty-one** to **two hundred thirty-three**, the **best possible**.
- The cost is more waiting: **thirty-seven** job-minutes, up from **thirteen**.

## Slide 12: all four instances (end by 7:21)

- Now our method on the **fresh** medium instance.

**Paste:** `pixi run solve out/video/fresh_medium out/video/medium_ig`

- About **three seconds**.

**Paste:** `pixi run check out/video/fresh_medium out/video/medium_ig/decision.json`

- Feasible. Weighted tardiness is **fifty-eight**, against **two thousand three hundred seventy-one**.
- Iterated greedy is **lower on all four** instances.
- **HiGHS** proves the two smallest results **optimal**.

## Slide 13: results by size (end by 7:43)

- The blue line at one hundred is E, D, D.
- The gain is **largest** at fifteen and forty-five jobs.
- At one hundred twenty jobs, other seeds did a little better, so the search has **not finished**.

## Slide 14: the stress test (end by 8:17)

- Now the key test, at a coefficient of variation of **zero point two**.
- Iterated greedy wins **all thirty** scenarios.
- Its mean is about **four hundred twenty** weighted minutes, against about **three thousand five hundred forty**.
- Mean waiting falls by **forty-eight percent**.
- For tardiness, the two groups of dots **do not overlap**.
- No hard constraint is broken in any scenario.

## Slide 15: more variability (end by 8:51)

- As variability grows, the **percentage** advantage falls at **every step**, from about **ninety-five** to about **twenty-seven**.
- But the **mean gain** holds, between about **two thousand six hundred** and **three thousand seven hundred** weighted minutes.
- E, D, D wins only **one** of the one hundred eighty scenarios.
- *(optional)* At the highest level, the gain in the weakest tenth of scenarios also drops.

## Slide 16: why this happens (end by 9:23)

- Why?
- E, D, D already has **thirty-four** late jobs, and delays make them **later**.
- Iterated greedy has **forty-one** on-time jobs.
- These numbers include delays passed on by the **jobs ahead**.
- Each one turns late **less often**: about **eighteen percent**, against **twenty-eight**.
- But it has **more to lose**: about **eight** turn late per scenario, against **three**.

## Slide 17: recommendation (end by 9:57)

- We recommend iterated greedy **on this line**.
- At zero point two, it saves about **three thousand** weighted minutes per period on average.
- Late jobs fall from about **thirty-six** to about **twelve**.
- The trade-off: it **cannot be traced by hand**, and it takes seconds.
- At very high variability the gain is **less dependable**, so **measure your line first**.

## Slide 18: limits (end by 10:18)

- The limits: **one generator**, and the stress test uses **one instance**.
- The noise is independent, and E, D, D is a **frozen list**.
- Next, we would add correlated delays and re-sequence when jobs are released.

## Slide 19: Don's walk-through (end by 10:53)

- Now each of us explains one part that **Claude Code** drafted.
- Mine is the **mixed-integer benchmark**.
- One thing was **wrong**: the agent solved the model **twice**.
- The solver said **eighty-one seconds**, but the command took more than **three minutes**.
- We compared the reported time with the **clock** and removed the second solve.
- A test now requires the optimum of **two hundred thirty-three**.

## Slide 20: Amir's walk-through (end by 11:33)

**Amir:**

- Hello. I am **Amir Ranjbar**.
- Mine is how we measure which on-time jobs are **at risk**.
- The agent compared a job's slack with the variation of its **own** processing times.
- That **misses delays** caused by the jobs ahead of it.
- So we used **simulated completion times** from the thirty saved scenarios.
- The jobs at risk changed from **three** in each sequence to **six of forty-one** and **four of eleven**.

## Slide 21: what we now know (end by 12:00)

**Don:**

- On exact data, iterated greedy cuts weighted tardiness by **eighty-one** to almost **ninety-nine** percent on the development instances.
- With wrong processing times, its fixed sequence wins **one hundred seventy-nine** of **one hundred eighty** scenarios.
- A plan can be wrong and **still have value**.
- **Thank you.**

Slides 22 and 23 list the sources. Show them for a moment at the end; there is nothing to say.
