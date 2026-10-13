"""Add-ons that are a skill (addon.yaml kind: skill + SKILL.md): what the portal's skill library accepts (its
limits on name, category, group and body) and what the skill relies on actually exists in the add-ons it requires."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ADDONS = Path(__file__).resolve().parents[1] / "addons"
SKILLS = sorted(path.parent for path in ADDONS.glob("*/addon.yaml")
                if yaml.safe_load(path.read_text(encoding="utf-8")).get("kind") == "skill")
# Tools of the add-ons a skill may require (Moza Connect's google-workspace plugin).
REQUIRED_TOOLS = {"google-workspace": {"gdrive_list", "gdrive_read", "gdrive_write", "gsheet_read", "gsheet_append"}}


def test_there_is_a_skill_add_on():
    assert [path.name for path in SKILLS] == ["khach-don-google-sheet"]


@pytest.mark.parametrize("addon", SKILLS, ids=lambda path: path.name)
def test_the_skill_fits_the_portal_skill_library(addon: Path):
    meta = yaml.safe_load((addon / "addon.yaml").read_text(encoding="utf-8"))
    assert meta["name"] == addon.name and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", meta["name"])
    assert re.fullmatch(r"moza-[a-z0-9-]{1,40}", meta["category"])
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", meta["biz_group"]) and len(meta["biz_group"]) <= 64
    assert 0 < len(meta["title"]) <= 255 and 0 < len(meta["description"]) <= 1024
    assert meta["customer_visible"] is True
    body = (addon / "SKILL.md").read_text(encoding="utf-8")
    assert 0 < len(body) <= 64000
    assert not body.startswith("---"), "the portal renders the frontmatter from its own columns"


@pytest.mark.parametrize("addon", SKILLS, ids=lambda path: path.name)
def test_every_tool_the_skill_names_comes_from_an_add_on_it_requires(addon: Path):
    meta = yaml.safe_load((addon / "addon.yaml").read_text(encoding="utf-8"))
    available = set().union(*(REQUIRED_TOOLS[name] for name in meta["requires"]))
    named = set(re.findall(r"`(g(?:drive|sheet)_[a-z_]+)`", (addon / "SKILL.md").read_text(encoding="utf-8")))
    assert named and named <= available
