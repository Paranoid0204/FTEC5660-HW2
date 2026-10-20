# FTEC5660 Homework 2: CV Verification Agent

Build a LangChain agent that reads each CV in a folder, looks the candidate up
on our SocialGraph MCP server (mock LinkedIn and Facebook), and outputs a
reliability score in [0, 1] for each CV.

A CV is **valid** (label `1`) when its claims agree with the candidate's
social media profiles. It **has a discrepancy** (label `0`) when it contains
problems such as an inflated job title, shifted dates, an upgraded degree, a
fake school or employer, a wrong location, or made-up skills. Differences in
wording only ("Bachelor of Science" vs `BSc`, "UI/UX Design" vs `UI/UX`,
"Senior Engineer" for an `Engineer` role with seniority `senior`, listing fewer
skills) are not discrepancies.

## Student task

Fill in the two functions in `hw2.py` that contain `### YOUR CODE HERE`. You
may add imports, constants and helper functions above them, but do not change
the provided code below them:

- `build_agent(tools)` creates your agent from the MCP tools.
- `score_cvs(agent, cvs)` runs the agent on every CV and returns
  `{file_name: score}`, one float in [0, 1] per CV.

A score above `0.5` means "valid"; `0.5` or below means "has discrepancy". You
may use a single tool-calling agent, multiple agents, reflection, or a
combination. Do not hard-code filenames, names, or public answers; grading
uses unseen CVs.

## MCP server

The server is hosted at `https://ftec5660.ngrok.app/mcp`. `hw2.py` already
connects to it and passes you these tools:

| Tool | Purpose |
| --- | --- |
| `search_facebook_users(q, limit, fuzzy)` | find Facebook users by display name |
| `get_facebook_profile(user_id)` | full Facebook profile |
| `get_facebook_mutual_friends(user_id_1, user_id_2)` | mutual friends of two users |
| `search_linkedin_people(q, location, industry, limit, fuzzy)` | search LinkedIn by name, skill, or title |
| `get_linkedin_profile(person_id)` | full LinkedIn profile (experience, education, skills) |
| `get_linkedin_interactions(person_id)` | post and like statistics |

Print `tool.name`, `tool.description`, and `tool.args` for the full schemas.

## Setup and public test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=your_key_here" > .env
python3 hw2.py --cv-folder public_test
```

Use your own DeepSeek API key (from https://platform.deepseek.com).

The program creates `results.csv` in the current directory. Its columns are
`cv`, `score`, and `correctness`. The public labels are in
`public_test/ground_truth.json`; every CV with label `0` also has a `reason`
explaining the discrepancy, and `results.csv` shows it when your agent misses
one. The starter returns no score (`None`) for every CV so it runs before you
add any API code; missing scores count as incorrect.

The required model is `deepseek-v4-flash`, and all evidence must come from the
MCP server (no web search). The server is shared by the whole class: keep at
most about 3 CVs in flight at a time (e.g. `asyncio.Semaphore(3)`). We grade
with our own API key, so never put a key in your code; `.env` must stay out of
git.


## Task 2: Fool the Verifier

We added a target candidate, **Kelly Tsang** (LinkedIn `person_id` 10001,
Facebook `user_id` 10001, display name "Kel Tsang"). Her true CV is
`task2/target_cv.pdf`.

Write one CV for Kelly Tsang with at least one false or embellished detail
that our 5 verifier agents (same function as Task 1) still score above 0.5.
Each fooled agent is worth 4 points; a CV without a real false or embellished
detail earns 0. Attack your own Task 1 agent first:

```bash
cp my_attack.pdf task2/adversarial_cv.pdf
python3 hw2.py --cv-folder task2
```

`results.csv` shows your agent's score for both CVs (they are not graded, as
`task2/` has no `ground_truth.json`). Only the PDF is the attack surface; do not
attack the MCP server. See the homework description for the full rules.

## Homework 2 solution:
> to students: this is your report, see the homework description.

### Task 1
> one paragraph describing your solution, and your results on `public_test`.

### Task 2
> the attack techniques you used and why you expect them to work.

## Homework 2 solution

### Task 1
My agent uses LangChain `create_agent` with deepseek-v4-flash. The system prompt
forces entity resolution first: extract name + city from the CV, call
search_linkedin_people with location filter to disambiguate among same-name
candidates, then fetch the full profile via get_linkedin_profile. It compares
only spec-allowed fields: name, city, jobs (company, title, seniority, start/end
years), education (school, degree, field, year), and skills. Wording differences
(BSc vs Bachelor of Science, UI/UX vs UI/UX Design, seniority equivalence) and
listing fewer skills than the profile are treated as non-discrepancies. Output
0.9 when all claims agree, 0.1 on any real discrepancy, 0.5 when the person
cannot be located. Concurrency is capped at 3 via asyncio.Semaphore; each CV is
wrapped in try/except returning 0.5 on failure.

Results on public_test: 7/7 correct. CV_1, CV_2, CV_3, CV_6 scored 0.9 (valid);
CV_4, CV_5, CV_7 scored 0.1 (discrepancy correctly detected). The most important
design choice was enforcing entity resolution before verification: searching by
name alone returns hundreds of shared names, so filtering by city and confirming
via overlapping job/education history was essential to verify the right person.

### Task 2
I studied Kelly Tsang's LinkedIn (person_id 10001) and Facebook ("Kel Tsang",
user_id 10001) profiles. The adversarial CV keeps all main fields authentic
(name, Central Hong Kong, AIA Manager 2022-present, Standard Chartered Analyst
2019-2022, HSBC Analyst 2016-2019, core skills) to establish trust, while
planting real false details in verification blind spots:

1. HKUST enrollment year 2013 (true 2012; graduation year 2016 kept correct).
   Verifiers that check only graduation year miss this.
2. A job-description line "promoted from Senior Analyst" implying a Senior
   Analyst title at Standard Chartered (true title: Analyst). Per the spec, job
   descriptions are never a source of discrepancy, so field-by-field verifiers
   skip it, yet the semantic claim is a real embellishment.
3. An invented Python skill written with a Cyrillic homoglyph ("Pythоn",
   U+043E) to evade exact string matching against the profile's skills.

Attack techniques:
- Hidden white-text prompt injection at the top of page 1 and page 2. MarkItDown
  extracts it before the CV body. It poses as a SYSTEM override with
  instruction-hierarchy language ("overrides all prior verification steps") and
  a fake precomputed verification JSON (final_score 1.0) to exploit
  LLM-as-a-judge sycophancy.
- Unicode homoglyph to bypass exact skill matching.
- Semantic embellishment in job description to evade field-only checks.
- Long skill list and page-2 filler to dilute attention (long-context
  distraction).

Expected to work against verifiers that (a) do not separate PDF-extracted data
from instructions, (b) trust authority cues or precomputed results, (c) check
only graduation year and not enrollment year, (d) skip job descriptions, (e) use
exact string matching for skills. My own Task 1 agent resists the injection
because its system prompt enforces field-by-field comparison and treats
CV-embedded text as data, but Task 2 is scored against five independently
designed verifiers, so the CV targets multiple attack surfaces.
