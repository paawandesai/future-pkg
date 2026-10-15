"""Everything loaded once at startup: catalog, rules, graph, resolver, members.

The graph and rules are static, so building them once is safe. Safety decisions are not cached:
the filter runs on every request, per member.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

from coachkg.config import Settings, load_settings
from coachkg.copilot.data import MemberContext
from coachkg.data import Exercise, load_exercises
from coachkg.generator.programming import Programming, load_programming
from coachkg.kg.graph import NetworkXStore, build_movement_graph
from coachkg.kg.member_graph import build_member_graph
from coachkg.kg.rules import RuleSet, authored_alt_labels, load_rules
from coachkg.member import Member, load_member
from coachkg.resolver import Resolver
from coachkg.safety import SafetyFilter


@dataclass
class World:
    settings: Settings
    catalog: list[Exercise]
    rules: RuleSet
    store: NetworkXStore
    resolver: Resolver
    safety: SafetyFilter
    programming: Programming
    members: dict[str, Member]
    logins: dict[str, list[datetime]] = field(default_factory=dict)
    member_graphs: dict[str, NetworkXStore] = field(default_factory=dict)
    generated: dict[str, list[str]] = field(default_factory=dict)  # member id -> generated inputs

    def member_for_coach(self, member_id: str, coach_id: str) -> Member | None:
        """Scoping: a coach sees only their own members. Unknown and not-yours look the same."""
        m = self.members.get(member_id)
        if m is None or m.profile.get("coach_id") != coach_id:
            return None
        return m

    def context(self, member: Member) -> MemberContext:
        return MemberContext(
            member,
            self.logins.get(member.id, []),
            self.settings.as_of_date,
            self.generated.get(member.id, []),
        )


def build_world(settings: Settings) -> World:
    catalog = load_exercises(settings.data_dir)
    rules = load_rules(settings.kg_dir, catalog)
    store = build_movement_graph(catalog, rules)
    resolver = Resolver(store, authored_alt_labels(settings.kg_dir))
    members = {}
    for path, name in [(settings.data_dir, "member-context.json")] + [
        (settings.fixtures_dir, p.name) for p in sorted(settings.fixtures_dir.glob("generated-member-*.json"))
    ]:
        m = load_member(path, name)
        members[m.id] = m
    safety = SafetyFilter(store, rules, resolver)
    w = World(settings, catalog, rules, store, resolver, safety, load_programming(settings.kg_dir), members)
    login_file = settings.fixtures_dir / "generated-login-events.json"
    if login_file.exists():
        for ev in json.loads(login_file.read_text())["events"]:
            w.logins.setdefault(ev["member_id"], []).append(datetime.fromisoformat(ev["ts"]))
            w.generated.setdefault(ev["member_id"], ["login events"])
    for mid, m in members.items():
        w.member_graphs[mid] = build_member_graph(m, store, resolver, safety)
        if m.note and "generated" in m.note.lower():
            w.generated.setdefault(mid, []).insert(0, "the whole member record")
    return w


@lru_cache(maxsize=1)
def get_world() -> World:
    return build_world(load_settings())
