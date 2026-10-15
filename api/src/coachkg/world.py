"""Everything loaded once at startup: catalog, rules, graph, resolver, members.

The graph and rules are static, so building them once is safe. Safety decisions are not cached:
the filter runs on every request, per member.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from coachkg.config import Settings, load_settings
from coachkg.data import Exercise, load_exercises
from coachkg.generator.programming import Programming, load_programming
from coachkg.kg.graph import NetworkXStore, build_movement_graph
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

    def member_for_coach(self, member_id: str, coach_id: str) -> Member | None:
        """Scoping: a coach sees only their own members. Unknown and not-yours look the same."""
        m = self.members.get(member_id)
        if m is None or m.profile.get("coach_id") != coach_id:
            return None
        return m


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
    return World(
        settings,
        catalog,
        rules,
        store,
        resolver,
        SafetyFilter(store, rules, resolver),
        load_programming(settings.kg_dir),
        members,
    )


@lru_cache(maxsize=1)
def get_world() -> World:
    return build_world(load_settings())
