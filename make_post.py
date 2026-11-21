"""Pick an unused SMLE question from the Cortiq bank and render question/answer slides.

Usage: python make_post.py [--qid N]
Writes out/01-question.html, out/02-answer.html, out/post.json and prints post.json.
Fix typos in out/post.json, then:  python make_post.py --render
Mark the question used only after it is published:  python make_post.py --mark N
"""
import html, json, random, re, sqlite3, sys
from pathlib import Path

DB = r"D:\AMMAR1\cortiq-live\data\smle-2025-2026\medos-smle-qbank.db"
HERE = Path(__file__).parent
USED = HERE / "used.txt"
OUT = HERE / "out"
LETTERS = "ABCDE"


def clean(s):
    s = re.sub(r"^medos-plain:", "", s or "").strip()
    return re.sub(r"^Better:\s*", "", s).strip()


def paragraphs(explanation):
    ps = [re.sub(r"<[^>]+>", "", p).strip() for p in re.findall(r"<p[^>]*>(.*?)</p>", clean(explanation), re.S)]
    body, key = [], ""
    for p in ps:
        if p.startswith("Answer:") or "AI-written" in p or "keyed answer" in p.lower():
            continue
        if p.startswith("Key point:"):
            key = p[len("Key point:"):].strip()
        else:
            body.append(p)
    return " ".join(body), key


def candidates(db, used):
    rows = db.execute(
        """select q.id, q.question, q.explanation, q.corrAns, s.name from Questions q join Subjects s on s.id=q.subId
           where q.explanation like '%Key point:%' and q.explanation not like '%keyed answer is incorrect%'
             and coalesce(q.mediaName,'')='' and coalesce(q.otherMedias,'') in ('','[]')
             and q.explanation not like '%may be incorrect%' and q.explanation not like '%Note:%'
             and length(q.question) between 60 and 520""").fetchall()
    for qid, stem, expl, corr, subject in rows:
        if str(qid) in used:
            continue
        answers = db.execute("select answerId, answerText from Answers where qId=? order by answerId", (qid,)).fetchall()
        choices = [clean(t) for _, t in answers]
        # skip OCR-noisy recalls: non-ASCII letters, "Ans" leftovers, overly long options
        if not 3 <= len(choices) <= 5 or any(not c or len(c) > 70 or re.search(r"[^\x00-\x7f]|\bAns\b", c) for c in choices):
            continue
        ids = [a for a, _ in answers]
        if corr not in ids:
            continue
        body, key = paragraphs(expl)
        if not key or len(body) > 650:
            continue
        yield dict(qid=qid, subject=subject, stem=clean(stem), choices=choices,
                   answer=LETTERS[ids.index(corr)], answer_text=choices[ids.index(corr)],
                   explanation=body, key_point=key)


def render(post):
    tpl = (HERE / "template" / "slide.html").read_text(encoding="utf-8")
    e = html.escape
    opts = "".join(f'<li><b>{LETTERS[i]}</b><span>{e(c)}</span></li>' for i, c in enumerate(post["choices"]))
    common = dict(SUBJECT=e(post["subject"]))
    q = dict(common, TAG="Question of the day", STEM=e(post["stem"]), BODY=f"<ul>{opts}</ul>",
             FOOT="Comment your answer below")
    ans = (f'<div class="answer"><h2>{post["answer"]}. {e(post["answer_text"])}</h2>'
           f'<p>{e(post["explanation"])}</p><div class="key"><b>Key point</b> {e(post["key_point"])}</div></div>')
    a = dict(common, TAG="Answer", STEM="", BODY=ans, FOOT="New SMLE question every day")
    OUT.mkdir(exist_ok=True)
    for name, vals in (("01-question.html", q), ("02-answer.html", a)):
        s = tpl
        for k, v in vals.items():
            s = s.replace("{{" + k + "}}", v)
        (OUT / name).write_text(s, encoding="utf-8")
    (OUT / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    args = sys.argv[1:]
    if args[:1] == ["--render"]:  # re-render after hand-fixing typos in out/post.json
        render(json.loads((OUT / "post.json").read_text(encoding="utf-8")))
        return
    if args[:1] == ["--mark"]:
        with USED.open("a") as f:
            f.write(args[1] + "\n")
        return
    used = set(USED.read_text().split()) if USED.exists() else set()
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    pool = list(candidates(db, used))
    if args[:1] == ["--qid"]:
        pool = [p for p in pool if p["qid"] == int(args[1])]
    assert pool, "no unused question left that passes the filters"
    post = random.choice(pool)
    post["pool_left"] = len(pool)
    render(post)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(post, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
