"""What this account is actually about — discovered, not guessed.

Keyword buckets do not work. The analyser this grew from tried them and left
49% of videos in "Other" while mislabelling much of the rest. So captions are
embedded and clustered instead, and the clusters are named by which terms
distinguish them rather than by which terms are common.

Two things here differ from the usual recipe, both because of who has to run it:

* **TF-IDF and k-means are implemented in pure Python.** scikit-learn plus
  sentence-transformers is roughly two gigabytes of wheels, which is not a
  reasonable thing to ask of someone who wants a content calendar. If
  sentence-transformers *is* installed the better embeddings are used
  automatically, and the report records which method ran.

* **k adapts to the catalogue.** A fixed k=10 shreds a 40-video account into
  noise and flattens a varied 3,000-video one. k is swept and chosen by
  silhouette score, bounded so that no cluster is too small to ever clear the
  significance threshold.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict

from ..stats import MIN_GROUP, concentration, effective_themes

#: Enough posts per cluster that a verdict is at least possible.
MIN_PER_CLUSTER = MIN_GROUP
MAX_CLUSTERS = 12
#: Silhouette is O(n^2); sample beyond this rather than crawl.
SILHOUETTE_SAMPLE = 300

_WORD = re.compile(r"[a-z][a-z'’]+")

STOPWORDS = set("""
a an the and or but if then than that this these those there here it its it's
i i'm im me my mine you you're your yours we we're our ours they them their
he she his her is are was were be been being am do does did doing done
have has had having will would shall should can could may might must
of in on at to for with from by as into over under about after before
not no yes so just now then too very much many more most some any all
what which who whom when where why how
one two three do don't dont cant can't get got go going goes come came
like likes really actually literally thing things way ways make makes made
let lets let's want wanted need needs know knows think thinks
today tomorrow yesterday day days week weeks month months year years
new old good bad best better big small little long short
guys guy girl girls people person everyone everybody someone somebody
fyp fypage foryou foryoupage viral trending trend tiktok reels reel
part pt ep episode video vid post follow followers link bio comment share
first second third fourth fifth last next another other others
finally already still yet ever never always sometimes often again
keep keeps kept showing shows show shown going gone went
hard easy quick quickly slow fast full half full
""".split())


# ------------------------------------------------------------------- vectorising

def tokenise(text: str) -> list[str]:
    """Words only, lowercased, stopwords dropped, hashtags split into words.

    Emoji and punctuation fall out naturally: they carry tone but almost no
    topical signal, and keeping them makes clusters form around decoration.
    """
    text = (text or "").lower()
    text = re.sub(r"#(\w+)", r" \1 ", text)      # #gymgirl -> gymgirl
    text = re.sub(r"https?://\S+", " ", text)
    words = _WORD.findall(text)
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def tfidf(docs: list[list[str]]) -> tuple[list[dict[str, float]], dict[str, float]]:
    """L2-normalised TF-IDF vectors as sparse dicts, plus the IDF table."""
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    vectors = []
    for d in docs:
        tf = Counter(d)
        vec = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        vectors.append({t: w / norm for t, w in vec.items()})
    return vectors, idf


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


# ------------------------------------------------------------------ spherical k-means

def _centroid(members: list[dict[str, float]]) -> dict[str, float]:
    acc: dict[str, float] = defaultdict(float)
    for v in members:
        for t, w in v.items():
            acc[t] += w
    norm = math.sqrt(sum(w * w for w in acc.values())) or 1.0
    return {t: w / norm for t, w in acc.items()}


def _kmeans(vectors: list[dict], k: int, seed: int = 7, iters: int = 25):
    """Spherical k-means with k-means++ seeding, on cosine similarity."""
    rng = random.Random(seed)
    n = len(vectors)
    # k-means++: spread the initial centres out rather than trusting luck
    centres = [vectors[rng.randrange(n)]]
    while len(centres) < k:
        d2 = []
        for v in vectors:
            best = max((cosine(v, c) for c in centres), default=0.0)
            d2.append(max(0.0, 1.0 - best) ** 2)
        total = sum(d2)
        if total <= 0:
            centres.append(vectors[rng.randrange(n)])
            continue
        pick = rng.random() * total
        run = 0.0
        for v, w in zip(vectors, d2):
            run += w
            if run >= pick:
                centres.append(v)
                break

    labels = [0] * n
    for _ in range(iters):
        moved = False
        for i, v in enumerate(vectors):
            best_j, best_s = 0, -2.0
            for j, c in enumerate(centres):
                s = cosine(v, c)
                if s > best_s:
                    best_j, best_s = j, s
            if labels[i] != best_j:
                labels[i], moved = best_j, True
        groups = defaultdict(list)
        for i, lab in enumerate(labels):
            groups[lab].append(vectors[i])
        centres = [_centroid(groups[j]) if groups.get(j) else centres[j]
                   for j in range(k)]
        if not moved:
            break
    return labels, centres


def _silhouette(vectors: list[dict], labels: list[int], k: int, seed: int = 7) -> float:
    """Mean silhouette on cosine distance, over a sample when the set is large."""
    rng = random.Random(seed)
    idx = list(range(len(vectors)))
    if len(idx) > SILHOUETTE_SAMPLE:
        idx = rng.sample(idx, SILHOUETTE_SAMPLE)
    by_label = defaultdict(list)
    for i in idx:
        by_label[labels[i]].append(i)
    if len(by_label) < 2:
        return -1.0

    scores = []
    for i in idx:
        own = by_label[labels[i]]
        if len(own) < 2:
            continue
        a = sum(1.0 - cosine(vectors[i], vectors[j]) for j in own if j != i) / (len(own) - 1)
        b = min(
            sum(1.0 - cosine(vectors[i], vectors[j]) for j in members) / len(members)
            for lab, members in by_label.items() if lab != labels[i] and members
        )
        denom = max(a, b)
        if denom > 0:
            scores.append((b - a) / denom)
    return sum(scores) / len(scores) if scores else -1.0


# ----------------------------------------------------------------------- naming

def _name_cluster(members: list[list[str]], idf: dict[str, float],
                  global_freq: Counter, total_docs: int) -> str:
    """Name by distinctiveness, not frequency.

    A cluster of gym videos is full of the word "gym", but so is the rest of a
    gym account. What names a cluster is the term that appears *more* here than
    it does everywhere else.
    """
    local = Counter()
    for d in members:
        local.update(set(d))
    n_local = len(members) or 1
    scored = []
    for term, count in local.items():
        if count < 2:
            continue
        local_rate = count / n_local
        global_rate = global_freq.get(term, 0) / total_docs
        lift = local_rate / (global_rate + 1e-9)
        if lift > 1.05:
            scored.append((lift * local_rate * idf.get(term, 1.0), term))
    scored.sort(reverse=True)
    picked = [t for _, t in scored[:3]]
    if not picked:
        picked = [t for t, _ in local.most_common(3)]
    return " / ".join(w.capitalize() for w in picked) or "Unlabelled"


# -------------------------------------------------------------------- entry point

def _try_embeddings(captions: list[str]):
    """Use sentence-transformers if it is already installed. Never install it."""
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        raw = model.encode(captions, normalize_embeddings=True,
                           show_progress_bar=False)
        # Reuse the sparse-dict machinery by treating dimensions as terms.
        return [{f"d{i}": float(x) for i, x in enumerate(row) if abs(x) > 1e-4}
                for row in raw]
    except Exception:
        return None


def choose_k(n_docs: int) -> list[int]:
    """Candidate k values, bounded so clusters can still clear significance."""
    ceiling = min(MAX_CLUSTERS, max(2, n_docs // MIN_PER_CLUSTER))
    return list(range(2, ceiling + 1))


def cluster(videos: list[dict], *, seed: int = 7, log=print) -> dict:
    """Assign every video a theme. Returns assignments, cluster rows and method."""
    captions = [(v.get("title") or "") for v in videos]
    docs = [tokenise(c) for c in captions]
    usable = [i for i, d in enumerate(docs) if len(d) >= 2]

    if len(usable) < MIN_PER_CLUSTER * 2:
        return _hashtag_fallback(videos, reason="too few usable captions to cluster")

    method = "tf-idf + k-means (pure python)"
    sub_docs = [docs[i] for i in usable]
    vectors, idf = tfidf(sub_docs)

    embedded = _try_embeddings([captions[i] for i in usable])
    if embedded:
        vectors = embedded
        method = "sentence-transformers (all-MiniLM-L6-v2) + k-means"

    candidates = []
    for k in choose_k(len(usable)):
        labels, _ = _kmeans(vectors, k, seed=seed)
        sizes = Counter(labels)
        if min(sizes.values()) < 2:
            continue
        score = _silhouette(vectors, labels, k, seed=seed)
        log(f"    k={k}: silhouette {score:+.3f}")
        candidates.append((score, k, labels))

    if not candidates:
        return _hashtag_fallback(videos, reason="no stable clustering found")

    # Silhouette on short captions is always small and usually flat — the gap
    # between k=4 and k=7 is routinely under 0.005, which is noise, not a
    # preference. Taking the strict maximum therefore picks an arbitrarily
    # large k and shatters the account into themes nobody can act on. So:
    # among everything statistically indistinguishable from the best, take the
    # *fewest* clusters. Fewer, larger themes are also more likely to clear the
    # significance threshold later.
    top = max(c[0] for c in candidates)
    tolerance = max(0.005, abs(top) * 0.10)
    plausible = [c for c in candidates if c[0] >= top - tolerance]
    score, k, labels = min(plausible, key=lambda c: c[1])
    if k != max(plausible, key=lambda c: c[0])[1]:
        log(f"    (k={max(plausible, key=lambda c: c[0])[1]} scored highest at "
            f"{top:+.3f}, but k={k} is within {tolerance:.3f} — taking the simpler split)")
    log(f"    chose k={k} (silhouette {score:+.3f}) via {method}")

    global_freq = Counter()
    for d in sub_docs:
        global_freq.update(set(d))

    by_label = defaultdict(list)
    for pos, lab in enumerate(labels):
        by_label[lab].append(pos)

    names: dict[int, str] = {}
    for lab, positions in by_label.items():
        names[lab] = _name_cluster([sub_docs[p] for p in positions], idf,
                                   global_freq, len(sub_docs))
    # Two clusters can land on the same distinctive terms; keep names unique so
    # the report's tables and charts do not silently merge them.
    seen: dict[str, int] = {}
    for lab in sorted(names):
        base = names[lab]
        if base in seen:
            seen[base] += 1
            names[lab] = f"{base} ({seen[base]})"
        else:
            seen[base] = 1

    assignments: dict[str, tuple[int, str]] = {}
    for pos, lab in enumerate(labels):
        v = videos[usable[pos]]
        assignments[v["video_id"]] = (int(lab), names[lab])
    for i, v in enumerate(videos):
        if i not in usable:
            assignments.setdefault(v["video_id"], (-1, "No caption"))

    counts = [len(by_label[lab]) for lab in sorted(by_label)]
    return {
        "assignments": assignments,
        "method": method,
        "k": k,
        "silhouette": round(score, 3),
        "concentration": round(concentration(counts), 3),
        "effective_themes": round(effective_themes(counts), 1),
        "fallback": False,
    }


def _hashtag_fallback(videos: list[dict], reason: str) -> dict:
    """When there is not enough caption text to cluster, group by the most
    common hashtag on each post. Crude, and the report says so."""
    from .aggregates import hashtags
    assignments: dict[str, tuple[int, str]] = {}
    tag_counts = Counter()
    for v in videos:
        tag_counts.update(hashtags(v))
    ranked = [t for t, _ in tag_counts.most_common(MAX_CLUSTERS)]
    index = {t: i for i, t in enumerate(ranked)}
    for v in videos:
        tags = [t for t in hashtags(v) if t in index]
        if tags:
            pick = min(tags, key=lambda t: index[t])
            assignments[v["video_id"]] = (index[pick], f"#{pick}")
        else:
            assignments[v["video_id"]] = (-1, "Untagged")
    counts = list(Counter(lab for lab, _ in assignments.values()).values())
    return {
        "assignments": assignments,
        "method": f"hashtag grouping ({reason})",
        "k": len(set(lab for lab, _ in assignments.values())),
        "silhouette": None,
        "concentration": round(concentration(counts), 3),
        "effective_themes": round(effective_themes(counts), 1),
        "fallback": True,
    }


# ------------------------------------------------------------------- the shortlist

def shortlist(theme_rows: list[dict], *, coverage: float = 0.70,
              demand: dict[str, float] | None = None) -> list[dict]:
    """Pick the themes worth building a month of content on.

    Ranked on reach index weighted by volume — a theme at 4% of output pulling
    3x reach beats one at 30% pulling average — then optionally nudged by
    external demand signal. Cut once the kept themes cover `coverage` of total
    posts, so the calendar is built from a handful of real strengths rather than
    from every cluster the algorithm happened to find.
    """
    if not theme_rows:
        return []
    demand = demand or {}
    scored = []
    for r in theme_rows:
        if r["name"] in ("No caption", "Untagged"):
            continue
        base = (r["index"] / 100.0) * math.sqrt(max(1, r["n"]))
        scored.append({**r, "score": round(base * (1.0 + demand.get(r["name"], 0.0)), 2)})
    scored.sort(key=lambda r: -r["score"])

    total_posts = sum(r["n"] for r in scored) or 1
    kept, running = [], 0
    for r in scored:
        kept.append(r)
        running += r["n"]
        if running / total_posts >= coverage and len(kept) >= 3:
            break
    return kept[:6]


def readable(name: str) -> str:
    """Turn a cluster label into something that reads inside a sentence.

    Cluster names are distinctive-term triples — "Workout / Glutes / First" —
    which are precise in a table and awful in prose: "Teach one thing about
    Workout / Glutes / First" is not a prompt anyone wants to act on. The top
    two terms, lowercased and joined, are close enough to a topic to be usable.
    """
    if not name:
        return "your main topic"
    if name in ("No caption", "Untagged"):
        return "your main topic"
    if name.startswith("#"):
        # Keep the word, drop the hash: "teach one thing about #glutesworkout"
        # reads like a tagging instruction rather than a subject.
        return name.lstrip("#").lower()
    terms = [t.strip().lower() for t in name.split("/") if t.strip()]
    if not terms:
        return name.lower()
    if len(terms) == 1:
        return terms[0]
    return f"{terms[0]} and {terms[1]}"


#: The creator-playbook loop — test variety, drop what does not perform, replace
#: it, repeat — expressed as a verdict per theme. Deliberately conservative:
#: nothing is called a loser without evidence, because telling someone to stop
#: making the thing they love on the strength of six posts is worse than useless.
CALLS = {
    "keep": ("Keep", "beats your average, proven"),
    "ditch": ("Ditch", "trails your average, proven"),
    "test": ("Test more", "not enough posts yet to judge either way"),
    "replace": ("Try", "outside demand this account has not covered"),
}


def calls(theme_rows: list[dict], *, gaps: list[str] | None = None) -> dict[str, dict]:
    """Map each theme to Keep / Ditch / Test more, plus any suggested additions."""
    out: dict[str, dict] = {}
    for r in theme_rows:
        proven = r.get("verdict") in ("strong", "moderate")
        if r["name"] in ("No caption", "Untagged"):
            key = "test"
        elif proven and r["index"] >= 105:
            key = "keep"
        elif proven and r["index"] <= 95:
            key = "ditch"
        else:
            key = "test"
        label, why = CALLS[key]
        out[r["name"]] = {"call": key, "label": label, "why": why}

    for topic in (gaps or []):
        label, why = CALLS["replace"]
        out.setdefault(topic, {"call": "replace", "label": label, "why": why})
    return out
