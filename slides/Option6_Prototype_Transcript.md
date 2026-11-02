# Prototype video transcript: one job sequence for an eight-stage line

This script goes with `Option6_Prototype_Slides.pdf`. It is planned for a calm pace of about 110 spoken words per minute. Read in full, with all three walk-throughs and the commands pasted, it takes about 9:07, under the 10-minute limit. With one presenter and one walk-through it takes about 8:07, and skipping every optional line saves about 0:26 more.

## How to use this script

- Read one line at a time, and pause briefly after each line.
- Pause a little longer when the slide changes.
- **Bold** words carry the stress.
- Say numbers the way they are spelled out in the script.
- Lines marked *(optional)* can be skipped if you are running long.
- Lines that start with **Paste** are terminal commands. Copy each one from this file, paste it, and press Enter. Pasting saves the time that typing would take. Keep talking while a command runs.
- It is fine to stop the recording between slides and start again.
- The time beside each slide heading is when that slide should end, with all three walk-throughs. With one walk-through, everything after it ends about one minute earlier.

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
| iteration | it-uh-**RAY**-shun |
| optimum, optimal | **OP**-tuh-mum, **OP**-tuh-mul |
| deviation | dee-vee-**AY**-shun |
| Gantt (the chart) | **GANT** |
| HiGHS (the solver) | like the word "highs" |
| EDD | say the letters: "E, D, D" |

## Slide 1: title (end by 0:11)

- Hello, I am **Muting Ma**.
- This is our prototype check-in for OM five twenty-two, **option six**.

## Slide 2: agenda (end by 0:17)

- The video has **five parts**, shown here.

## Slide 3: the decision (end by 1:08)

- A planner must choose the **order** of jobs on the line.
- Every job visits the **same eight stages**, and jobs **cannot pass** each other.
- So **one sequence** holds at every stage.
- Each job has a **release time**, a **due date**, and a **weight**.
- Our main measure is **total weighted tardiness**: how late the jobs are, weighted by importance.
- Our second measure is the **waiting time** between stages.
- *(optional)* We added three assumptions, shown on the right.
- A job that is **slow at a later stage** holds up **every job behind it**.

## Slide 4: the rule to beat (end by 2:28)

- The rule to beat is **earliest due date**, or **E, D, D**.
- We sort the jobs by **due date**, break ties by job number, and start each operation **as early as possible**.
- Job **one** is released at minute **thirteen**, so it starts stage one at thirteen.
- Job **two** was released at **eight**, but it must **wait** for stage one until **twenty-four**.
- First, I run the tests.

**Paste:** `pixi run test`

- All **thirty-one** tests pass. Now the rule on the hand-checkable case.

**Paste:** `pixi run solve data/hand_checkable out/video/hand_rule --method rule`

- Weighted tardiness is **two hundred eighty-one**, and waiting is **thirteen** minutes.
- Now the checker compares it with the worked example.

**Paste:** `pixi run check data/hand_checkable out/video/hand_rule/decision.json --expect data/worked-example/metrics.json`

- The schedule is **feasible**, and **every measure matches**. This is **test one**.

## Slide 5: the checker (end by 3:42)

- The checker is **separate code**. It reads only the **input files** and the **decision**.
- It checks that each job appears **once**, each operation has the **right length**, release and stage order hold, and each stage runs **one job at a time**.
- Then it **recomputes** every measure by itself.
- Now I copy the medium instance to a **new folder**. This is a **fresh** instance.

**Paste (macOS, Linux, or WSL):** `mkdir -p out/video && cp -r data/development_medium out/video/fresh_medium`

**Paste (PowerShell instead):** `New-Item -ItemType Directory -Force out/video; Copy-Item -Recurse data/development_medium out/video/fresh_medium`

**Paste:** `pixi run solve out/video/fresh_medium out/video/medium_rule --method rule`

**Paste:** `pixi run check out/video/fresh_medium out/video/medium_rule/decision.json`

- The rule's schedule is **feasible**, with weighted tardiness **two thousand three hundred seventy-one**.
- Finally, the **edge case** has a processing time of **zero**.

**Paste:** `pixi run solve data/edge_case out/video/edge`

- The tool **rejects** it, names the **file**, the **column**, and the **line**, and writes **no decision**.

## Slide 6: the researched method (end by 4:40)

- Our researched method is **iterated greedy**, from **Ruiz** and **Stützle**, two thousand eight.
- They built it for flow shops with **setup times** and **weighted tardiness**. Our line has **no setups**, so every setup time is **zero**.
- E, D, D looks only at **due dates**. It **ignores** weights, release times, and processing times.
- Iterated greedy compares sequences by their **real weighted tardiness** on all eight stages, so a **heavy** job can move ahead of a **light** one.
- In the authors' tests, it had the **lowest average deviation** of all the methods they tested.
- *(optional)* Neither paper has release times. Our timing includes them in every step.

## Slide 7: how it builds, improves, and stops (end by 5:40)

- A solution is simply a **sequence** of jobs.
- **Step one**: order the jobs by **due date divided by weight**, and insert each one at its **best position**.
- **Step two**, local search: take each job out and put it back at its best position, until **nothing improves**.
- Then we **repeat**: remove **four jobs** at random, put them back at their best positions, and search again.
- We always accept a **better** sequence.
- *(optional)* Sometimes we also accept a worse one, with a small probability, so the search does not get stuck.
- We **stop** after **five thousand** iterations, with a fixed seed, so a rerun gives the **same answer**.

## Slide 8: the hand-checkable case (end by 6:26)

- On the hand-checkable case, the method finds the **optimum**.
- The **top** chart is E, D, D. The **bottom** chart is iterated greedy. **Darker** bars mean **higher weight**.
- E, D, D puts job **five**, with weight **one**, before jobs **three** and **four**, with weight **four**.
- Iterated greedy moves job five to the **end**.
- Weighted tardiness falls from **two hundred eighty-one** to **two hundred thirty-three**, the **best possible** of all **seven hundred twenty** sequences.
- The cost is more waiting: **thirty-seven** minutes, up from **thirteen**.

## Slide 9: first results against the rule (end by 7:25)

- Now the researched method on the **fresh** medium instance.

**Paste:** `pixi run solve out/video/fresh_medium out/video/medium_ig`

- It takes about **three seconds**.

**Paste:** `pixi run check out/video/fresh_medium out/video/medium_ig/decision.json`

- The checker confirms it. Weighted tardiness is **fifty-eight**, against **two thousand three hundred seventy-one** for the rule.
- The table shows that iterated greedy is **lower on all four** instances.
- A solver called **HiGHS** proves that two hundred thirty-three and twenty-one are **optimal** on the two smallest cases.
- *(optional)* At one hundred twenty jobs, the search needs more iterations.
- For the final submission, we will **stress-test** both plans when processing times **vary**.

## Slides 10 to 12: walk-throughs

Each member presents a different slide. With one presenter, choose one slide and skip the other two.

### Slide 10: the checker's messages (end by 7:52)

- **Claude Code** drafted the **checker**. It **names every violation** it finds.
- One thing was **wrong**: messages printed times as decimals, like "twenty-three **point zero**".
- Our data are **whole minutes**, so we **fixed** the format, and our tests now check each message.

### Slide 11: the best-position search (end by 8:19)

- **Claude Code** drafted the **best-position search**. It tries one job at **every position**.
- One thing was **unclear**: it stops checking a position **early**. Could it **miss** the best one?
- **No**, because tardiness and waiting only **grow** as jobs are added. A test on **twenty** random cases agrees.

### Slide 12: the method's start and temperature (end by 8:52)

- **Claude Code** drafted the **researched method**. Its first plan ordered the start by **due date only**, with a temperature factor of **zero point four**.
- The weighted tardiness paper uses **due date divided by weight**, and **zero point five**.
- We **read the paper**, fixed both, and our tests show it reaches the **optimum** on the small case.

## Slide 13: summary (end by 9:07)

- To summarize: the rule **reproduces** the worked example, the checker **confirms** every decision, and iterated greedy **beats the rule** on all four instances.
- **Thank you.**

Slide 14 lists the sources. Show it for a moment at the end; there is nothing to say.
