"""Significance testing, in pure standard library.

The analyser this grew out of used `scipy.stats.ttest_ind`, and degraded to
"n/a (scipy missing)" when it wasn't installed. That degradation is unacceptable
here — the verdict is the thing that stops a weak finding reading as advice, so
it has to work on a machine where the user ran nothing but `pip install yt-dlp
openpyxl`. scipy is also a large wheel and a compiler dependency on Windows.

So Welch's t-test and the Student-t tail are implemented directly against
`math.lgamma`. `test_against_scipy()` at the bottom checks this agrees with
scipy to 1e-12 when scipy happens to be available.
"""
from __future__ import annotations

import math

#: Groups smaller than this are never called significant, however large the gap.
#: Eight is inherited from the original analyser and is deliberately cautious:
#: a handful of posts can look like a pattern purely by chance.
MIN_GROUP = 8

STRONG_P = 0.01
MODERATE_P = 0.05

#: Verdicts, and the plain-language wording used on the report's front pages.
PLAIN = {
    "strong": "solid evidence",
    "moderate": "early signal",
    "too early to tell": "not enough data yet",
}


# ----------------------------------------------------- regularised incomplete beta

def _betacf(a: float, b: float, x: float) -> float:
    """Continued-fraction expansion for the incomplete beta (Lentz's method)."""
    MAXIT, EPS, FPMIN = 300, 3.0e-16, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    front = math.exp(lbeta)
    # The continued fraction converges fast only on one side of the mean;
    # use the symmetry I_x(a,b) = 1 - I_(1-x)(b,a) for the other.
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_sf(t: float, df: float) -> float:
    """Two-sided survival function for Student's t."""
    if df <= 0 or math.isnan(t) or math.isinf(df):
        return 1.0
    return betai(df / 2.0, 0.5, df / (df + t * t))


# ------------------------------------------------------------------ Welch's t-test

def _mean_var(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return m, v


def welch(a: list[float], b: list[float]) -> tuple[float, float, float]:
    """Welch's unequal-variance t-test. Returns (t, df, two-sided p)."""
    if len(a) < 2 or len(b) < 2:
        return (0.0, 0.0, 1.0)
    ma, va = _mean_var(a)
    mb, vb = _mean_var(b)
    na, nb = len(a), len(b)
    sa, sb = va / na, vb / nb
    denom = sa + sb
    if denom <= 0:
        return (0.0, 0.0, 1.0)
    t = (ma - mb) / math.sqrt(denom)
    # Welch-Satterthwaite degrees of freedom
    dl = (sa * sa) / (na - 1) + (sb * sb) / (nb - 1)
    if dl <= 0:
        return (t, 0.0, 1.0)
    df = (denom * denom) / dl
    return (t, df, t_sf(t, df))


def verdict_for(p: float) -> str:
    if math.isnan(p):
        return "too early to tell"
    if p < STRONG_P:
        return "strong"
    if p < MODERATE_P:
        return "moderate"
    return "too early to tell"


def welch_verdict(group_views: list[int], rest_views: list[int]) -> tuple[float, str]:
    """Is the gap between two groups real?

    Tested on log(views), because view distributions are heavily right-skewed
    and the raw scale lets one viral post carry a whole group. Groups under
    MIN_GROUP videos are never called significant.
    """
    if len(group_views) < MIN_GROUP or len(rest_views) < MIN_GROUP:
        return (1.0, "too early to tell")
    a = [math.log1p(max(0, v)) for v in group_views]
    b = [math.log1p(max(0, v)) for v in rest_views]
    _, _, p = welch(a, b)
    if math.isnan(p):
        return (1.0, "too early to tell")
    return (float(p), verdict_for(p))


def plain(verdict: str) -> str:
    """Front-page wording. Statistics stay on the method page."""
    return PLAIN.get(verdict, verdict)


def posts_needed(group: list[int], rest: list[int]) -> int | None:
    """Roughly how many more posts before this comparison could be decided.

    "Not enough data yet" is the honest answer for most findings on most
    accounts, and as a bare verdict it is also a dead end — it tells someone
    their work is unmeasurable without telling them what would change that.
    This turns it into a number they can act on.

    The estimate: |t| grows about as sqrt(n), so to reach the 0.05 threshold
    the group needs roughly n * (1.96 / |t|)^2 posts. Below the minimum group
    size the answer is simply the shortfall. Returns None when the gap is
    already decided or is so small that no realistic number of posts would
    settle it.
    """
    if len(group) < MIN_GROUP:
        return MIN_GROUP - len(group)
    if len(rest) < MIN_GROUP:
        return None

    a = [math.log1p(max(0, v)) for v in group]
    b = [math.log1p(max(0, v)) for v in rest]
    t, _, p = welch(a, b)
    if p < MODERATE_P:
        return None                      # already answered
    if abs(t) < 1e-6:
        return None                      # no gap to detect at any sample size
    needed = len(a) * (1.96 / abs(t)) ** 2
    extra = int(math.ceil(needed - len(a)))
    if extra <= 0:
        return None
    # Past a couple of months of posting the number stops being advice. "About
    # 106 more posts on this theme" is arithmetically right and practically
    # useless — it reads as "never". Say nothing rather than something
    # discouraging and unactionable.
    return extra if extra <= 40 else None


# ------------------------------------------------------------- distribution shape

def entropy(counts: list[int]) -> float:
    """Shannon entropy in bits. Used for the style-concentration score:
    a feed spread thinly over twenty themes has no recognisable style, one
    concentrated in three does."""
    total = sum(counts)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def concentration(counts: list[int]) -> float:
    """Herfindahl index over theme shares. 1.0 = everything in one theme,
    approaching 0 = scattered thinly over many.

    Deliberately NOT entropy normalised by the number of themes: that makes a
    tidy 3-theme feed and a scattered 20-theme feed score identically, which
    throws away the thing being measured. Herfindahl keeps the ordering —
    3 even themes score 0.33, 20 even themes score 0.05.
    """
    total = sum(counts)
    if total <= 0:
        return 0.0
    return sum((c / total) ** 2 for c in counts if c > 0)


def effective_themes(counts: list[int]) -> float:
    """How many themes the feed *reads as*, which is rarely how many it has.

    The inverse Herfindahl. A feed of 12 themes where one holds 80% of the
    posts reads as roughly 1.6 styles, not 12 — and that is the number a
    creator should see.
    """
    h = concentration(counts)
    return (1.0 / h) if h > 0 else 0.0


# ------------------------------------------------------------------------- self-test

def test_against_scipy() -> str:
    """Cross-check against scipy when it happens to be installed. Not a runtime
    dependency — this exists so the pure-Python path can be proven, not trusted."""
    try:
        import numpy as np
        from scipy import stats as sp
    except ImportError:
        return "scipy not installed - skipped"
    import random
    random.seed(7)
    worst = 0.0
    for _ in range(200):
        na, nb = random.randint(8, 200), random.randint(8, 200)
        a = [random.lognormvariate(random.uniform(4, 9), random.uniform(0.4, 2.5))
             for _ in range(na)]
        b = [random.lognormvariate(random.uniform(4, 9), random.uniform(0.4, 2.5))
             for _ in range(nb)]
        _, _, mine = welch(a, b)
        _, theirs = sp.ttest_ind(np.array(a), np.array(b), equal_var=False)
        worst = max(worst, abs(mine - float(theirs)))
    return f"max abs p-value difference vs scipy over 200 trials: {worst:.3e}"


if __name__ == "__main__":
    print(test_against_scipy())
