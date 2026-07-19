from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from tender.eval.golden import (
    DEFAULT_MANIFEST_PATH,
    load_manifest,
    validate_release_corpus,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RELEASE_PATH = REPO_ROOT / "data" / "tender" / "evaluation_release.yaml"


class CustomerQualityGateError(RuntimeError):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = tuple(reasons)
        super().__init__(
            "Tender customer quality gate is blocked: " + "; ".join(reasons)
        )


def assert_customer_release_approved(
    *,
    release_path: Path = DEFAULT_RELEASE_PATH,
    corpus_path: Path = DEFAULT_MANIFEST_PATH,
) -> None:
    release = _read_mapping(release_path)
    reasons: list[str] = []
    status = release.get("status")
    if status != "approved":
        reasons.append(f"release status is {status or 'missing'}")

    evaluation = _mapping(release.get("evaluation"))
    if evaluation.get("passed") is not True:
        reasons.append("evaluation has not passed")
    if not evaluation.get("report"):
        reasons.append("evaluation report is not recorded")

    qs_review = _mapping(release.get("qs_review"))
    if qs_review.get("status") != "approved":
        reasons.append("QS review is not approved")
    for field in ("reviewer", "reviewed_at", "report"):
        if not qs_review.get(field):
            reasons.append(f"QS review {field} is not recorded")

    rollout = _mapping(release.get("rollout"))
    if rollout.get("status") != "approved":
        reasons.append("customer rollout is not approved")
    if not rollout.get("rollback_procedure"):
        reasons.append("customer rollback procedure is not recorded")

    frozen = _mapping(release.get("frozen_versions"))
    for field in (
        "taxonomy",
        "report_language",
        "extract_prompt",
        "classification_prompt",
        "mapping_prompt",
        "silence_prompt",
        "extract_model",
        "adjudication_model",
    ):
        if not frozen.get(field):
            reasons.append(f"frozen version {field} is not recorded")

    reasons.extend(validate_release_corpus(load_manifest(corpus_path)).errors)
    if reasons:
        raise CustomerQualityGateError(reasons)


def _read_mapping(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as file:
        value = yaml.safe_load(file)
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a mapping")
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
