# Judgment Framework

For each part of the tool: **Who does it?** / **What if it is wrong?** / **How do we catch it?**
(If mam's three questions are worded differently, rename the column headings to match.)

| Part of the tool | Who does it? | What if it is wrong? | How do we catch it? |
|---|---|---|---|
| Read the post and extract criteria | LLM | May guess a branch, convert a percentage, or invent a value | Python validator and fact checks; prompt tells it to use null when unsure |
| Validate the JSON reply | Python (`is_valid`) | A bad reply could crash the run or pass wrong types | Retry once, then fall back to empty values and `needs_review` |
| Fact-check against the post | Python (`check_facts`) | A value not in the post could be trusted | Anything not written in the post becomes empty or null |
| Job status | Python (`job_status`) | A vague post could be matched anyway | No branch or no CGPA means `needs_review`, listed in `review.csv` |
| Match students | Python (`is_eligible`) | A student is wrongly left out or wrongly included | Exact rules, `float()` for CGPA, eval harness with hand-worked counts |
| Final list | Human (placement officer) | A wrong list reaches a company or a student | Every list is a **draft**; officer checks before sharing |

## Wrongly left out vs wrongly included

| | Student wrongly LEFT OUT | Student wrongly INCLUDED |
|---|---|---|
| Harm | Eligible student misses an opportunity and may never know | Company gets a list with an ineligible student; college looks careless |
| Visible? | Hard to notice (the student is simply absent) | Easier to notice (a wrong name is on the list) |
| Our choice | Prefer sending unclear posts to `needs_review` instead of guessing | Strict fact checks stop invented criteria |

Leaving out is harder to spot, so unclear posts go to a human rather than being guessed.

**Human checkpoint:** the placement officer checks every list and every `review.csv` post before anything is shared.
