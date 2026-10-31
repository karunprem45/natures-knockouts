"""The round loop for one gene.

NOTHING IN THIS LOOP ASSIGNS WORK. Agents post artifacts and needs to a shared board; in round 1
every agent looks at the board itself and bids on the open need it is able to answer; in round 2
the skeptic reads everything and any agent that received answers or challenges decides whether to
revise. The loop only enforces the shared call budget (R1), the same cap every arm has.

round 0  burden, gwas, tolerance, safety post evidence independently (parallel)
round 1  open needs ranked by pressure; each capable agent picks up its best one -> fulfillment
round 2  skeptic posts challenges; agents with answers or challenges post a revision
score    scoring.py, pure Python
"""
from concurrent.futures import ThreadPoolExecutor
import config
from board.needs import NeedIndex
from llm.guards import BudgetExceeded

# calls kept back in round 1 so the skeptic and at least one revision still fit the budget
RESERVE_AFTER_ROUND1 = 3


def _remaining(client, gene_code):
    return client.budget.cap - client.budget.used[(client.arm, gene_code)]


def _safe(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except BudgetExceeded:
        return None


def run_gene(gene_code, agents, skeptic, client, store, use_skeptic=True):
    """agents: {name: Agent}. Returns every artifact posted for this gene, in order."""
    posted = []

    def post(a):
        if a is not None:
            store.append(a)
            posted.append(a)
        return a

    # round 0: independent evidence
    names = sorted(agents)
    with ThreadPoolExecutor(len(names)) as pool:
        r0 = dict(zip(names, pool.map(lambda n: _safe(agents[n].evidence, gene_code, 0), names)))
    for n in names:
        post(r0[n])

    index = NeedIndex()
    for a in posted:
        index.post_from(a, depth=0)

    # round 1: each agent inspects the board and bids on the need it can best answer
    fulfilments = []
    while _remaining(client, gene_code) > RESERVE_AFTER_ROUND1:
        bids = []
        for n in names:
            if any(f.producer_agent == n for f in fulfilments):
                continue          # one answer per agent per round
            need, pressure = index.best_for(n, current_round=1)
            if need is not None:
                bids.append((pressure, need.need_id, n, need))
        if not bids:
            break
        pressure, _, n, need = sorted(bids, key=lambda b: (-b[0], b[1]))[0]
        index.consume(need)
        parent = next(a for a in posted if a.artifact_id == need.parent_artifact_id)
        f = _safe(agents[n].fulfil, gene_code, {"query": need.query, "rationale": need.rationale}, parent, 1)
        if f is None:
            break
        post(f.add_flag(f"pressure:{pressure:.2f}"))
        fulfilments.append(f)

    # round 2a: the skeptic reviews every artifact for the gene
    challenges = []
    if use_skeptic and _remaining(client, gene_code) > 0:
        c = post(_safe(skeptic.review, gene_code, list(posted), 2))
        if c is not None and c.artifact_type == "challenge":
            challenges = c.challenges

    # round 2b: agents that received answers or challenges may revise; most-affected first
    by_parent = {}
    for f in fulfilments:
        if f.artifact_type == "fulfillment":
            requester = next(a for a in posted if a.artifact_id == f.parent_artifact_ids[0]).producer_agent
            by_parent.setdefault(requester, []).append(f)
    affected = sorted({*by_parent, *(c["channel"] for c in challenges)} & set(names),
                      key=lambda n: (-(len(by_parent.get(n, [])) + sum(c["channel"] == n for c in challenges)), n))
    for n in affected:
        if _remaining(client, gene_code) <= 0 or r0.get(n) is None or r0[n].artifact_type != "evidence":
            continue
        mine = [c for c in challenges if c["channel"] == n]
        post(_safe(agents[n].revise, gene_code, r0[n], mine, by_parent.get(n, []), 2))
    return posted
