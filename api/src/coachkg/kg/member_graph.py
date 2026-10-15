"""Member graph (KG 2). It joins the movement graph only through shared concept nodes:
equipment, body regions and exercises.

Provenance: record fields are `dataset`; chat lines are `member-said` or `coach-said`. The safety
filter never reads this graph's chat edges, so a member's words cannot clear an injury.
"""

from __future__ import annotations

from coachkg.kg.graph import Edge, NetworkXStore
from coachkg.member import Member
from coachkg.resolver import Resolver
from coachkg.safety import SafetyFilter

SOURCE = "member-context.json"


def build_member_graph(
    member: Member, movement: NetworkXStore, resolver: Resolver, safety: SafetyFilter
) -> NetworkXStore:
    g = NetworkXStore()
    mid = f"member:{member.id}"
    g.add_node(mid, kind="member", label=member.name, fictional=True)

    def shared(node: str) -> None:
        if node not in g.g:
            g.add_node(node, **movement.node(node))

    for q in member.equipment_available:
        r = resolver.resolve(q, ["equipment"])
        if r.status == "accepted" and r.concept:
            shared(r.concept)
            g.add_edge(Edge(mid, r.concept, "has-equipment", "dataset", f"{SOURCE} equipment_available"))

    for inj in member.injuries:
        node = f"injury:{inj.id}"
        g.add_node(node, kind="injury", label=inj.region, status=inj.status, active=inj.active)
        g.add_edge(Edge(mid, node, "has-injury", "dataset", f"{SOURCE} injuries"))
        region = safety.region_for_injury(inj.joint, inj.region)
        if region and region in movement.g:
            shared(region)
            g.add_edge(Edge(node, region, "located-at", "dataset", f"{SOURCE} injuries.joint"))

    for w in member.workout_history:
        node = f"session:{w['date']}"
        g.add_node(node, kind="session", label=w.get("title"), completed=w.get("completed"), date=w["date"])
        g.add_edge(Edge(mid, node, "scheduled", "dataset", f"{SOURCE} workout_history"))
        for name in w.get("exercises", []):
            r = resolver.resolve(str(name), ["exercise"])
            if r.status == "accepted" and r.concept:
                shared(r.concept)
                g.add_edge(
                    Edge(
                        node,
                        r.concept,
                        "included",
                        "dataset",
                        f"{SOURCE} workout_history",
                        {"match": r.method},
                    )
                )

    for i, m in enumerate(member.chat_history):
        node = f"message:{i}"
        g.add_node(node, kind="message", ts=m.ts, provenance=m.provenance)
        g.add_edge(
            Edge(mid, node, "sent" if m.provenance == "member-said" else "received", m.provenance, SOURCE)
        )
        for bm in resolver.find_body_mentions(m.text):
            if bm.resolution.status == "accepted" and bm.resolution.concept:
                shared(bm.resolution.concept)
                g.add_edge(
                    Edge(node, bm.resolution.concept, "mentions", m.provenance, f"{SOURCE} chat_history")
                )
    return g
