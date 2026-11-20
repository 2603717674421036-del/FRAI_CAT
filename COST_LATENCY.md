# Cost and Latency Note

**Assumption:** the placement cell receives several posts a week. We plan for a busy day of **10 posts**.

| Item | Estimate |
|---|---|
| API calls per day | 10 (one per post), at most 20 if every post needs the one retry |
| Time per call | about 1 to 3 seconds for a small model (measure on your own key and note the real number) |
| Time for a whole day | under 1 minute (calls run one after another) |
| Tokens per call | about 950 (system prompt ~800, post ~60, reply ~80) |
| Tokens per day | about 10,000 (about 19,000 in the worst case) |
| Cost per day | **free** on a free-tier key; on a paid key, tokens per day x price per million tokens (at an example price of $1 per million, about $0.01 to $0.02 per day) |

Student matching is plain Python: no API calls, no cost, instant.

Update the latency and price lines with real numbers after your first full run.
