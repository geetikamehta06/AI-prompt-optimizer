"""
Framework Registry — loads, queries, and manages prompt engineering frameworks.

All framework definitions live in config/frameworks.yaml.
All framework prompt templates live in src/frameworks/templates/*.j2.
Adding a new framework requires zero code changes — just YAML + template.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from ..models.framework import Framework, FrameworkField
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)

# Default paths
_FRAMEWORKS_CONFIG = "config/frameworks.yaml"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


class FrameworkRegistry:
    """Registry for all prompt engineering frameworks.
    
    Loads frameworks from YAML config and provides query/filter methods.
    Templates are rendered via Jinja2 for maximum flexibility.
    """

    def __init__(self, config_path: str = _FRAMEWORKS_CONFIG) -> None:
        self._frameworks: dict[str, Framework] = {}
        self._jinja_env: Optional[Environment] = None
        self._load_frameworks(config_path)
        self._init_templates()

    def _load_frameworks(self, config_path: str) -> None:
        """Load all frameworks from YAML config."""
        path = Path(config_path)
        if not path.exists():
            logger.error("Frameworks config not found: %s", config_path)
            return

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        frameworks_list = raw.get("frameworks", [])
        for fw_data in frameworks_list:
            fields = [FrameworkField(**f) for f in fw_data.get("fields", [])]
            fw = Framework(
                id=fw_data["id"],
                name=fw_data["name"],
                acronym=fw_data.get("acronym", ""),
                description=fw_data.get("description", ""),
                category=fw_data.get("category", "general"),
                complexity=fw_data.get("complexity", "moderate"),
                enabled=fw_data.get("enabled", True),
                fields=fields,
                best_for=fw_data.get("best_for", []),
                combinable_with=fw_data.get("combinable_with", []),
            )
            self._frameworks[fw.id] = fw

        logger.info("Loaded %d frameworks from %s", len(self._frameworks), config_path)

    def _init_templates(self) -> None:
        """Initialize Jinja2 template environment."""
        if _TEMPLATES_DIR.exists():
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(_TEMPLATES_DIR)),
                trim_blocks=True,
                lstrip_blocks=True,
            )

    # ── Query Methods ───────────────────────────────────────

    def get(self, framework_id: str) -> Optional[Framework]:
        """Get a framework by ID."""
        return self._frameworks.get(framework_id)

    def get_all(self, enabled_only: bool = True) -> list[Framework]:
        """Get all frameworks, optionally filtered to enabled only."""
        frameworks = list(self._frameworks.values())
        if enabled_only:
            frameworks = [f for f in frameworks if f.enabled]
        return frameworks

    def get_by_category(self, category: str) -> list[Framework]:
        """Get frameworks by category."""
        return [f for f in self._frameworks.values()
                if f.enabled and f.category == category]

    def get_by_use_case(self, use_case: str) -> list[Framework]:
        """Get frameworks that match a use case tag."""
        use_lower = use_case.lower()
        return [f for f in self._frameworks.values()
                if f.enabled and any(use_lower in bf.lower() for bf in f.best_for)]

    def get_compatible_chains(self, framework_id: str) -> list[Framework]:
        """Get frameworks that can be chained with the given framework."""
        fw = self.get(framework_id)
        if not fw:
            return []
        return [self._frameworks[cid]
                for cid in fw.combinable_with
                if cid in self._frameworks and self._frameworks[cid].enabled]

    def search(self, query: str) -> list[Framework]:
        """Search frameworks by name, description, or best_for tags."""
        q = query.lower()
        results = []
        for fw in self._frameworks.values():
            if not fw.enabled:
                continue
            if (q in fw.name.lower() or
                    q in fw.description.lower() or
                    any(q in bf.lower() for bf in fw.best_for)):
                results.append(fw)
        return results

    # ── Template Rendering ──────────────────────────────────

    def render_template(self, framework_id: str, **context: str) -> Optional[str]:
        """Render a framework's Jinja2 prompt template with context variables."""
        if not self._jinja_env:
            logger.warning("No template environment — templates dir missing")
            return None

        template_name = f"{framework_id}.j2"
        try:
            template = self._jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.warning("Template render failed for %s: %s", framework_id, e)
            return None

    def get_framework_summary(self, framework_id: str) -> str:
        """Get a compact summary of a framework for AI context."""
        fw = self.get(framework_id)
        if not fw:
            return ""

        fields_str = " · ".join(f.name for f in fw.fields)
        return (
            f"{fw.name} ({fw.acronym}): {fw.description}\n"
            f"Fields: {fields_str}\n"
            f"Best for: {', '.join(fw.best_for)}"
        )

    def get_all_summaries(self) -> str:
        """Get summaries of all enabled frameworks for AI context."""
        summaries = []
        for fw in self.get_all(enabled_only=True):
            fields_str = " · ".join(f.name for f in fw.fields)
            summaries.append(
                f"- {fw.id}: {fw.name} ({fw.acronym}) — {fw.description}\n"
                f"  Fields: {fields_str}\n"
                f"  Best for: {', '.join(fw.best_for)}"
            )
        return "\n\n".join(summaries)

    @property
    def count(self) -> int:
        """Number of registered frameworks."""
        return len(self._frameworks)

    @property
    def enabled_count(self) -> int:
        """Number of enabled frameworks."""
        return len([f for f in self._frameworks.values() if f.enabled])
