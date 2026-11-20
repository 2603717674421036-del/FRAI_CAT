"""Placement Eligibility Checker.

Flow: load CSVs -> LLM reads each post -> Python validates + fact-checks the
reply -> job status -> match students -> write 4 report files.
Student records NEVER go to the LLM. Every list is a DRAFT for the placement
officer to check before it is shared.
"""
import csv
import json
import os
import re

from llm_client import call_llm

BRANCHES = ["CSE", "IT", "AIDS", "ECE", "EEE", "MECH", "CIVIL"]
FIELDS = ["branches", "min_cgpa", "max_backlogs", "batch", "summary"]
EMPTY = {"branches": [], "min_cgpa": None, "max_backlogs": None, "batch": None,
         "summary": "LLM reply unusable"}

# How each branch may be written in a post. IT is case-sensitive so the
# ordinary word "it" is not mistaken for the branch.
BRANCH_PATTERNS = {
    "CSE": (r"\bCSE\b|computer science", re.I),
    "IT": (r"\bIT\b|information technology", 0),
    "AIDS": (r"AI\s*&\s*DS|AI\s*/\s*DS|\bAIDS\b|AI and DS|artificial intelligence", re.I),
    "ECE": (r"\bECE\b|electronics and communication", re.I),
    "EEE": (r"\bEEE\b|electrical and electronics", re.I),
    "MECH": (r"\bMECH\b|mechanical", re.I),
    "CIVIL": (r"\bcivil\b", re.I),
}


# ---------- loading ----------
def load_jobs(path):
    """Read jobs.csv into a list of dictionaries (id, company, post)."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_students(path):
    """Read students.csv; CGPA is converted with float() (text would compare wrongly)."""
    students = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                students.append({"roll": row["roll"].strip(), "name": row["name"].strip(),
                                 "branch": row["branch"].strip().upper(),
                                 "cgpa": float(row["cgpa"]),
                                 "backlogs": int(row["backlogs"]),
                                 "batch": int(row["batch"])})
            except (ValueError, KeyError):
                print(f"  skipped bad student row: {row}")    # one bad row must not stop the run
    return students


# ---------- LLM reply: parse + validate ----------
def parse_reply(text):
    """Turn the LLM's text into a dictionary (removes ``` fences if present)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def is_valid(reply):
    """True only if the reply has the five fields with allowed values."""
    if not isinstance(reply, dict) or any(k not in reply for k in FIELDS):
        return False
    b = reply["branches"]
    if not isinstance(b, list) or any(x not in BRANCHES + ["ALL"] for x in b):
        return False
    if "ALL" in b and len(b) > 1:
        return False
    c = reply["min_cgpa"]
    if c is not None and (isinstance(c, bool) or not isinstance(c, (int, float)) or not 0 <= c <= 10):
        return False
    m = reply["max_backlogs"]
    if m is not None and (isinstance(m, bool) or not isinstance(m, int) or m < 0):
        return False
    y = reply["batch"]
    if y is not None and (isinstance(y, bool) or not isinstance(y, int) or not 2000 <= y <= 2100):
        return False
    return isinstance(reply["summary"], str)


def read_criteria(post):
    """Ask the LLM about one post. Validate; retry once; otherwise fall back.
    Returns (criteria with ONLY the five fields, note)."""
    for attempt in (1, 2):
        try:
            reply = parse_reply(call_llm(post))
            if is_valid(reply):
                return {k: reply[k] for k in FIELDS}, ""      # copy only the five fields
            note = "invalid LLM reply"
        except Exception as e:                                # network, JSON, key errors...
            note = f"LLM error: {type(e).__name__}"
    return dict(EMPTY), note + " (after retry)"


# ---------- fact checks ----------
def _number_written(value, post):
    """True if the number appears in the post and is not a percentage."""
    forms = {str(value), f"{value:.1f}"}
    if float(value).is_integer():
        forms.add(str(int(value)))
    for form in forms:
        for m in re.finditer(r"(?<![\d.])" + re.escape(form) + r"(?!\d|\.\d)", post):
            tail = post[m.end():m.end() + 12].lower().lstrip()
            if not tail.startswith(("%", "percent", "per cent")):
                return True
    return False


def check_facts(post, criteria):
    """Keep only what is really written in the post. Returns (clean, removed notes)."""
    clean, removed = dict(criteria), []
    if clean["branches"] == ["ALL"]:
        if not re.search(r"any branch|all branches", post, re.I):
            clean["branches"] = []
            removed.append("ALL not written in post")
    else:
        kept = []
        for b in clean["branches"]:
            pattern, flags = BRANCH_PATTERNS[b]
            if re.search(pattern, post, flags):
                kept.append(b)
            else:
                removed.append(f"branch {b} not named in post")
        clean["branches"] = kept
    if clean["min_cgpa"] is not None and not _number_written(clean["min_cgpa"], post):
        removed.append(f"CGPA {clean['min_cgpa']} not written in post (percentage or guess)")
        clean["min_cgpa"] = None
    if clean["batch"] is not None and not re.search(rf"\b{clean['batch']}\b", post):
        removed.append(f"batch {clean['batch']} not written in post")
        clean["batch"] = None
    if clean["max_backlogs"] is not None and not re.search(r"backlog|arrear", post, re.I):
        removed.append("backlog limit not written in post")
        clean["max_backlogs"] = None
    clean["summary"] = " ".join(str(clean["summary"]).split()[:12])    # 12 words max
    return clean, removed


def job_status(criteria):
    """needs_review if no branches or no CGPA, otherwise matched."""
    if not criteria["branches"] or criteria["min_cgpa"] is None:
        return "needs_review"
    return "matched"


def review_reason(criteria, removed, note):
    """Plain-English reason the placement officer must read this post."""
    reasons = list(removed)
    if note:
        reasons.append(note)
    if not criteria["branches"]:
        reasons.append("no branch could be confirmed")
    if criteria["min_cgpa"] is None:
        reasons.append("no CGPA cut-off confirmed")
    return "; ".join(dict.fromkeys(reasons))


# ---------- matching ----------
def is_eligible(student, c):
    """All stated rules must pass: branch, CGPA, backlogs (if stated), batch (if stated)."""
    if c["branches"] != ["ALL"] and student["branch"] not in c["branches"]:
        return False
    if student["cgpa"] < c["min_cgpa"]:
        return False
    if c["max_backlogs"] is not None and student["backlogs"] > c["max_backlogs"]:
        return False
    if c["batch"] is not None and student["batch"] != c["batch"]:
        return False
    return True


def process_job(job, students):
    """Run one job through LLM -> validate -> fact check -> status -> matching."""
    criteria, note = read_criteria(job["post"])
    criteria, removed = check_facts(job["post"], criteria)
    status = job_status(criteria)
    eligible = [s for s in students if is_eligible(s, criteria)] if status == "matched" else []
    reason = review_reason(criteria, removed, note) if status == "needs_review" else ""
    return {"job": job, "criteria": criteria, "status": status, "eligible": eligible, "reason": reason}


# ---------- reports ----------
def write_reports(results, students, out_dir="output"):
    """Write job_summary.csv, eligible.csv, review.csv and summary.txt."""
    os.makedirs(out_dir, exist_ok=True)
    with open(f"{out_dir}/job_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "company", "branches", "min_cgpa", "max_backlogs", "batch",
                    "summary", "status", "eligible_count"])
        for r in results:
            c = r["criteria"]
            w.writerow([r["job"]["id"], r["job"]["company"], "|".join(c["branches"]),
                        c["min_cgpa"], c["max_backlogs"], c["batch"], c["summary"],
                        r["status"], len(r["eligible"])])
    with open(f"{out_dir}/eligible.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "company", "roll", "name", "branch", "cgpa", "backlogs", "batch"])
        for r in results:
            for s in r["eligible"]:
                w.writerow([r["job"]["id"], r["job"]["company"], s["roll"], s["name"],
                            s["branch"], s["cgpa"], s["backlogs"], s["batch"]])
    with open(f"{out_dir}/review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "company", "post", "reason"])
        for r in results:
            if r["status"] == "needs_review":
                w.writerow([r["job"]["id"], r["job"]["company"], r["job"]["post"], r["reason"]])
    covered = {s["roll"] for r in results for s in r["eligible"]}
    with open(f"{out_dir}/summary.txt", "w", encoding="utf-8") as f:
        f.write("DRAFT - placement officer must check before sharing\n\nEligible count per job:\n")
        for r in results:
            f.write(f"  {r['job']['id']} {r['job']['company']}: {len(r['eligible'])} ({r['status']})\n")
        f.write("\nStudents eligible for no job yet:\n")
        left = [s for s in students if s["roll"] not in covered]
        for s in left:
            f.write(f"  {s['roll']} {s['name']} ({s['branch']}, CGPA {s['cgpa']})\n")
        if not left:
            f.write("  (none)\n")


def main():
    jobs = load_jobs("jobs.csv")
    students = load_students("students.csv")
    results = []
    for job in jobs:
        r = process_job(job, students)
        print(f"{job['id']} {r['status']:<12} eligible={len(r['eligible'])}")
        results.append(r)
    write_reports(results, students)
    print("Done. Draft reports written to output/ - placement officer must check them.")


if __name__ == "__main__":
    main()
