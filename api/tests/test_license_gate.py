"""The CI licence gate (scripts/license_audit.py): what it must block and what it must let through."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from coachkg.config import REPO_ROOT


def _forbidden() -> re.Pattern[str]:
    spec = importlib.util.spec_from_file_location(
        "license_audit", Path(REPO_ROOT, "scripts", "license_audit.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pattern: re.Pattern[str] = module.FORBIDDEN
    return pattern


FORBIDDEN = _forbidden()

BLOCKED = [
    "GNU General Public License v3 (GPLv3)",
    "AGPL-3.0-or-later",
    "SSPL-1.0",
    "BUSL-1.1",
    "CC-BY-NC-4.0",
    "UNKNOWN",
    "Unknown",
    "(MIT OR GPL-3.0)",
    "(MIT OR GPL-3.0-or-later)",
    "GPL-2.0-only",
    "GPLv2+",
    "GNU General Public License v3.0",
    "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007",
    "GNU Affero General Public License v3",
    "Server Side Public License, v 1",
    "BSL-1.1",
    "BSL 1.1",
    "Business Source License 1.1",
    "Creative Commons Attribution Non Commercial 4.0",
    "Attribution-NonCommercial 4.0 International",
    "CC BY-NC-SA 4.0",
    "PolyForm-Noncommercial-1.0.0",
    "PolyForm-Small-Business-1.0.0",
    "Research use only",
    "UNLICENSED",
    "",
    "SEE LICENSE IN LICENSE.md",
    "Proprietary",
    "Apache-2.0 WITH Commons-Clause",
]

ALLOWED = [
    "LGPL",
    "GNU Lesser General Public License v3 (LGPLv3)",
    "GNU Library General Public License v2",
    "LGPL-2.1-or-later",
    "Elastic-2.0",
    "NCSA",
    "BSL-1.0",
    "MIT",
    "MIT License",
    "MPL-2.0",
    "BlueOak-1.0.0",
    "Unlicense",
    "CC-BY-4.0",
    "Python-2.0",
    "Apache Software License; BSD License",
    "OFL-1.1",
    "MIT AND ISC",
]


@pytest.mark.parametrize("licence", BLOCKED)
def test_gate_blocks(licence: str) -> None:
    assert FORBIDDEN.search(licence), licence


@pytest.mark.parametrize("licence", ALLOWED)
def test_gate_allows(licence: str) -> None:
    assert not FORBIDDEN.search(licence), licence


def test_every_licence_in_licenses_md_passes() -> None:
    text = Path(REPO_ROOT, "LICENSES.md").read_text()
    rows = re.findall(r"^\| ([^|]+) \| ([^|]+) \| ([^|]*) \|$", text, re.M)
    licences = {lic.strip() for name, _, lic in rows if name.strip() not in ("Package", "Tool")}
    assert licences and not [lic for lic in licences if FORBIDDEN.search(lic)]


def test_skos_export_states_rights_and_source_licences() -> None:
    ttl = Path(REPO_ROOT, "kg", "export", "coachkg-skos.ttl").read_text()
    assert "dcterms:rights" in ttl
    assert "dcterms:license <https://creativecommons.org/licenses/by/3.0/>" in ttl
    assert "dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/>" in ttl
