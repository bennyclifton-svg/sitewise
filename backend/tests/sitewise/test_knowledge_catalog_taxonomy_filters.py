from pathlib import Path

from app.sitewise import knowledge_catalog
from app.sitewise.knowledge_catalog import CatalogEntry


def _entry(
    path: str,
    *,
    tier: str = "topic",
    loaded_by: str | None = None,
    subclasses: tuple[str, ...] | None = None,
    work_scopes: tuple[str, ...] | None = None,
    required_by: dict[str, int] | None = None,
) -> CatalogEntry:
    return CatalogEntry(
        path=path,
        title=path,
        tier=tier,
        loaded_by=loaded_by,
        topics=(),
        summary="Test entry",
        applies_to_roles=None,
        applies_to_archetypes=None,
        applies_to_classes=("commercial",),
        applies_to_work_types=("refurb",),
        applies_to_subclasses=subclasses,
        applies_to_work_scopes=work_scopes,
        required_by=required_by or {},
        doctrine_anchors=(),
        sections=(),
    )


def test_file_catalog_reads_subclass_and_work_scope_frontmatter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "scoped-guide.md"
    source.write_text(
        """---
tier: topic
applies_to_subclasses: [office, retail]
applies_to_work_scopes: [fire_services, electrical_power]
---
# Scoped guide
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        knowledge_catalog,
        "_KNOWLEDGE_SOURCES",
        (("seed", tmp_path),),
    )
    monkeypatch.setattr(knowledge_catalog, "DOCTRINE_PATH", "missing-doctrine.md")
    knowledge_catalog.file_catalog.cache_clear()

    try:
        entry = knowledge_catalog.file_catalog()[0]
        assert entry.applies_to_subclasses == ("office", "retail")
        assert entry.applies_to_work_scopes == (
            "fire_services",
            "electrical_power",
        )
    finally:
        knowledge_catalog.file_catalog.cache_clear()


def test_applicable_entries_match_any_selected_subclass_and_work_scope(
    monkeypatch,
) -> None:
    universal = _entry("seed/universal.md")
    office = _entry("seed/office.md", subclasses=("office",))
    warehouse = _entry("seed/warehouse.md", subclasses=("warehouse",))
    services = _entry(
        "seed/services.md",
        work_scopes=("fire_services", "electrical_power"),
    )
    monkeypatch.setattr(
        knowledge_catalog,
        "file_catalog",
        lambda: (universal, office, warehouse, services),
    )

    entries = knowledge_catalog.applicable_entries(
        building_class="commercial",
        work_type="refurb",
        subclasses=("office", "retail"),
        work_scopes=("electrical_power",),
    )

    assert [entry.path for entry in entries] == [
        "seed/universal.md",
        "seed/office.md",
        "seed/services.md",
    ]


def test_empty_selected_axes_exclude_scoped_entries_but_not_unfiltered_entries(
    monkeypatch,
) -> None:
    universal = _entry("seed/universal.md")
    office = _entry("seed/office.md", subclasses=("office",))
    services = _entry("seed/services.md", work_scopes=("fire_services",))
    monkeypatch.setattr(
        knowledge_catalog,
        "file_catalog",
        lambda: (universal, office, services),
    )

    entries = knowledge_catalog.applicable_entries(
        building_class="commercial",
        work_type="refurb",
        subclasses=(),
        work_scopes=(),
    )

    assert [entry.path for entry in entries] == ["seed/universal.md"]


def test_required_and_applicable_path_interfaces_thread_taxonomy_axes(
    monkeypatch,
) -> None:
    role = _entry(
        "seed/role.md",
        tier="role-overlay",
        loaded_by="user_role: architect-pm",
    )
    office = _entry(
        "seed/office.md",
        subclasses=("office",),
        required_by={"create-pmp": 3},
    )
    warehouse = _entry(
        "seed/warehouse.md",
        subclasses=("warehouse",),
        required_by={"create-pmp": 3},
    )
    fire = _entry(
        "seed/fire.md",
        work_scopes=("fire_services",),
        required_by={"create-pmp": 4},
    )
    monkeypatch.setattr(
        knowledge_catalog,
        "file_catalog",
        lambda: (role, office, warehouse, fire),
    )

    required = knowledge_catalog.required_paths_by_workflow(
        archetype=None,
        building_class="commercial",
        work_type="refurb",
        subclasses=("office",),
        work_scopes=("fire_services",),
        workflows=("create-pmp",),
    )
    applicable = knowledge_catalog.applicable_platform_paths(
        archetype=None,
        building_class="commercial",
        work_type="refurb",
        subclasses=("office",),
        work_scopes=("fire_services",),
    )

    assert required["create-pmp"] == [
        knowledge_catalog.DOCTRINE_PATH,
        "seed/role.md",
        "seed/office.md",
        "seed/fire.md",
    ]
    assert "seed/warehouse.md" not in applicable
    assert {"seed/office.md", "seed/fire.md"}.issubset(applicable)
