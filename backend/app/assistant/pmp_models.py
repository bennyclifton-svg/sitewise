"""PMP workflow model selection and trace metadata."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

PMP_OPENAI_CHAT_PROVIDER = "openai-chat"
PMP_OPENAI_API_PROVIDER = "openai-api"
PMP_CODEX_PROVIDER = "openai-codex"
PMP_OPENAI_RESPONSES_PROVIDER = "openai-responses"
PMP_ALLOWED_PROVIDERS = frozenset(
    {
        PMP_OPENAI_CHAT_PROVIDER,
        PMP_OPENAI_API_PROVIDER,
        PMP_CODEX_PROVIDER,
    }
)


class InvalidPmpModelError(ValueError):
    """Raised when a PMP workflow model option is malformed."""


@dataclass(frozen=True)
class PmpModelSpec:
    provider: str
    model: str
    label: str
    configured_id: str
    source: str
    execution_provider: str
    execution_id: str


def _default_label(provider: str, model: str) -> str:
    if provider == PMP_CODEX_PROVIDER:
        return f"{model} (Codex)"
    return model


def _split_provider_model(raw: str, *, default_provider: str) -> tuple[str, str]:
    if ":" not in raw:
        return default_provider, raw
    provider, model = raw.split(":", 1)
    return provider.strip(), model.strip()


def _validate_provider(provider: str) -> str:
    if provider not in PMP_ALLOWED_PROVIDERS:
        allowed = ", ".join(sorted(PMP_ALLOWED_PROVIDERS))
        raise InvalidPmpModelError(
            f"Unsupported PMP model provider {provider!r}. Allowed providers: {allowed}"
        )
    return provider


def _execution_provider(provider: str) -> str:
    if provider == PMP_OPENAI_API_PROVIDER:
        return PMP_OPENAI_RESPONSES_PROVIDER
    if provider == PMP_CODEX_PROVIDER:
        # The PMP workflows require PydanticAI typed output. PydanticAI does not
        # expose an ``openai-codex`` provider, so execute through its OpenAI chat
        # structured-output provider and make that adapter explicit in metadata.
        return PMP_OPENAI_CHAT_PROVIDER
    return provider


def resolve_pmp_model(override: str | None = None) -> PmpModelSpec:
    """Resolve the model used by Create PMP and Update PMP workflows.

    A plain request override is treated as a legacy OpenAI chat model override.
    A provider-qualified value such as ``openai-codex:gpt-5.5`` records the
    intended provider in trace/provenance while passing the model id to the
    structured PydanticAI runner.
    """
    raw_override = override.strip() if override else ""
    raw = raw_override or settings.pmp_model
    source = "request" if raw_override else "PMP_MODEL"
    default_provider = (
        PMP_OPENAI_CHAT_PROVIDER if raw_override else settings.pmp_model_provider
    )
    provider, model = _split_provider_model(raw.strip(), default_provider=default_provider)
    provider = _validate_provider(provider)
    if not model:
        raise InvalidPmpModelError("PMP model must not be blank.")

    label = (
        settings.pmp_model_label
        if not raw_override and settings.pmp_model_label.strip()
        else _default_label(provider, model)
    )
    return PmpModelSpec(
        provider=provider,
        model=model,
        label=label,
        configured_id=f"{provider}:{model}",
        source=source,
        execution_provider=_execution_provider(provider),
        execution_id=f"{_execution_provider(provider)}:{model}",
    )


def pmp_model_metadata(spec: PmpModelSpec) -> dict[str, str]:
    return {
        "model": spec.model,
        "model_label": spec.label,
        "model_provider": spec.provider,
        "model_config_id": spec.configured_id,
        "model_source": spec.source,
        "model_execution_provider": spec.execution_provider,
        "model_execution_id": spec.execution_id,
    }
