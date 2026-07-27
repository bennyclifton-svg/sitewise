from pathlib import Path

import pytest

from tender.eval.release_gate import (
    CustomerQualityGateError,
    assert_customer_release_approved,
)


def test_default_customer_quality_gate_is_blocked_with_evidence() -> None:
    release_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "tender"
        / "evaluation_release.yaml"
    )

    with pytest.raises(CustomerQualityGateError) as caught:
        assert_customer_release_approved(release_path=release_path)

    assert "release status is blocked" in caught.value.reasons
    assert "evaluation has not passed" in caught.value.reasons
    assert "QS review is not approved" in caught.value.reasons
    assert "customer rollout is not approved" in caught.value.reasons
    assert any("30 real documents" in reason for reason in caught.value.reasons)
