from types import SimpleNamespace

from app.sitewise.archetype_bridge import effective_taxonomy


def _project(**overrides):
    values = {
        "building_class": None,
        "work_type": None,
        "archetype": None,
        "project_metadata": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_new_taxonomy_columns_win_over_legacy_archetype() -> None:
    taxonomy = effective_taxonomy(
        _project(
            building_class="commercial",
            work_type="new",
            archetype="renovation",
            project_metadata={"taxonomy": {"subclasses": ["office"]}},
        )
    )

    assert taxonomy.building_class == "commercial"
    assert taxonomy.work_type == "new"
    assert taxonomy.subclasses == ("office",)


def test_metadata_subclass_objects_resolve_to_values() -> None:
    taxonomy = effective_taxonomy(
        _project(
            building_class="commercial",
            work_type="refurb",
            archetype="renovation",
            project_metadata={
                "taxonomy": {"subclasses": [{"value": "other", "label": "Lab"}]}
            },
        )
    )

    assert taxonomy.subclasses == ("other",)


def test_legacy_new_dwelling_mapping() -> None:
    assert effective_taxonomy(_project(archetype="new-dwelling")) == (
        "residential",
        "new",
        ("house",),
    )


def test_legacy_renovation_mapping() -> None:
    assert effective_taxonomy(_project(archetype="renovation")) == (
        "residential",
        "refurb",
        ("house",),
    )


def test_legacy_multi_dwelling_mapping() -> None:
    assert effective_taxonomy(_project(archetype="multi-dwelling")) == (
        "residential",
        "new",
        ("townhouses",),
    )


def test_legacy_ancillary_mapping() -> None:
    assert effective_taxonomy(_project(archetype="ancillary")) == (
        "residential",
        "extend",
        ("other",),
    )


def test_legacy_small_commercial_mapping() -> None:
    assert effective_taxonomy(_project(archetype="small-commercial")) == (
        "commercial",
        None,
        ("other",),
    )


def test_missing_taxonomy_and_archetype_returns_empty_effective_taxonomy() -> None:
    assert effective_taxonomy(_project()) == (None, None, ())
