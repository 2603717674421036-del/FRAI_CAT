# Placement Eligibility Checker

CIT AI-Native Engineering Programme, Semester 1, Assessment 5.
Team: Tevin, Rahul, Heshna, Anushka.

A console tool that reads job posts, uses an LLM to extract the eligibility
criteria, **fact-checks them in Python**, and writes a **draft** list of eligible
students per job. **Student records never go to the LLM.** The placement officer
checks every list before it is shared.

## How it works

1. Load `jobs.csv` and `students.csv`
2. Send each **post only** to the LLM (prompt in `system_prompt.txt`)
3. Validate the JSON reply (`is_valid`), retry once, else fall back
4. Fact-check (`check_facts`): branches, CGPA and batch must be written in the post
5. Status (`job_status`): `matched` or `needs_review`
6. Match students (`is_eligible`) for matched jobs
7. Write reports (`write_reports`) into `output/`

## Preview page

Open `preview/index.html` in any browser (double-click). It shows the job posts, draft eligible lists and test results from an offline run. No internet or server is needed.

## Setup

```bash
# Python 3.9+, no extra libraries needed
cp .env.example .env        # then put your own API key in .env (never commit it)
python placement_checker.py # full run
python eval_harness.py      # 5 eval posts + 3 red-team inputs
```

`.env` settings: `LLM_PROVIDER` (`gemini` or `anthropic`), `LLM_API_KEY`, optional `LLM_MODEL`.
`LLM_PROVIDER=mock` runs an offline fake LLM for testing only. Use a real key for the final run and results.

## Files

| File | Purpose |
|---|---|
| `placement_checker.py` | Main program (load, read_criteria, is_valid, check_facts, job_status, is_eligible, write_reports) |
| `llm_client.py` | Sends one post to the LLM; key read from environment |
| `system_prompt.txt` | 5-role prompt: Authority, Exemplar, Constraint, Rubric, Metadata |
| `jobs.csv`, `students.csv` | Inputs (10 posts, 26 made-up students) |
| `eval_harness.py` | 5 eval posts and 3 red-team tests, expected values worked out by hand |
| `JUDGMENT_FRAMEWORK.md` | Judgment Framework table |
| `COST_LATENCY.md` | Cost and latency note |
| `output/` | `job_summary.csv`, `eligible.csv`, `review.csv`, `summary.txt` |

## Safety rules built in

- API key only in `.env` (listed in `.gitignore`)
- Only the five JSON fields are copied from the LLM reply
- Percentages are never converted to CGPA
- Branches must be named in the post (never guessed from the job role)
- CGPA read with `float()`, never as text
