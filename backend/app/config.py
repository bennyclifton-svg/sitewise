import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_storage_bucket: str = "project-files"
    database_url: str
    openai_api_key: str
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_models: str = (
        "gpt-4.1-nano,gpt-4o-mini,gpt-4.1-mini,gpt-4.1,gpt-4o,o4-mini,o3-mini"
    )
    log_level: str = "INFO"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    allowed_origins: str = "http://localhost:5173,http://localhost:5174"
    data_dir: Path = _BACKEND_DIR.parent / "data"
    ingest_embedding_batch_size: int = 64
    ingest_supported_extensions: str = ".pdf,.docx,.md"
    retrieval_semantic_limit: int = 20
    retrieval_fts_limit: int = 20
    retrieval_final_limit: int = 10
    retrieval_rrf_k: int = 60
    retrieval_neighbour_before: int = 1
    retrieval_neighbour_after: int = 1
    assistant_context_passage_limit: int = 6
    assistant_passage_content_chars: int = 800
    whole_document_content_chars: int = 12000
    whole_document_passage_limit: int = 3
    openai_rate_limit_max_retries: int = 5
    pmp_hybrid_compiler: bool = True
    cost_plan_hybrid_compiler: bool = True
    public_app_url: str = "http://localhost:5173"
    polar_enabled: bool = False
    polar_environment: str = "sandbox"
    polar_access_token: str | None = None
    polar_webhook_secret: str | None = None
    polar_starter_product_id: str | None = None
    polar_professional_product_id: str | None = None
    polar_checkout_success_path: str = "/billing?checkout=success"
    polar_customer_portal_return_path: str = "/billing"
    tender_odl_hybrid_enabled: bool = True
    tender_page_render_dpi: int = 150
    tender_worker_poll_seconds: float = 2.0
    tender_worker_concurrency: int = 4
    tender_job_max_attempts: int = 3
    tender_job_backoff_base_seconds: int = 30
    tender_job_stale_lock_minutes: int = 10
    tender_model_extract: str = "gpt-4.1-mini"
    tender_model_adjudicate_small: str = "gpt-4.1-mini"
    tender_model_adjudicate_frontier: str = "gpt-4.1"
    tender_embed_model: str = "text-embedding-3-small"
    tender_embedding_dimensions: int = 1536
    tender_extraction_confidence_threshold: float = 0.85
    tender_reconciliation_tolerance: float = 0.01
    tender_t0_trgm_threshold: float = 0.92
    tender_t1_accept_sim: float = 0.80
    tender_t1_accept_margin: float = 0.10
    tender_t2_accept_conf: float = 0.80
    tender_t3_review_conf: float = 0.70
    tender_silence_ps_sim: float = 0.60
    tender_silence_review_conf: float = 0.75

    @field_validator("database_url")
    @classmethod
    def reject_transaction_pooler(cls, value: str) -> str:
        if "pooler.supabase.com" in value and ":6543" in value:
            msg = (
                "DATABASE_URL must not use the transaction pooler (port 6543). "
                "Use the direct connection or session pooler (port 5432)."
            )
            raise ValueError(msg)
        if "pgbouncer=true" in value.lower():
            msg = (
                "DATABASE_URL must not use transaction-mode pooler (pgbouncer=true). "
                "Use the direct connection or session pooler (port 5432)."
            )
            raise ValueError(msg)
        return value

    @field_validator("polar_environment")
    @classmethod
    def validate_polar_environment(cls, value: str) -> str:
        if value not in {"sandbox", "production"}:
            raise ValueError("POLAR_ENVIRONMENT must be sandbox or production")
        return value

    @model_validator(mode="after")
    def require_polar_settings_when_enabled(self) -> "Settings":
        if not self.polar_enabled:
            return self

        missing = [
            name
            for name, value in {
                "POLAR_ACCESS_TOKEN": self.polar_access_token,
                "POLAR_WEBHOOK_SECRET": self.polar_webhook_secret,
                "POLAR_STARTER_PRODUCT_ID": self.polar_starter_product_id,
                "POLAR_PROFESSIONAL_PRODUCT_ID": self.polar_professional_product_id,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                f"Polar is enabled, but these settings are missing: {', '.join(missing)}"
            )
        return self

    @model_validator(mode="after")
    def validate_tender_embedding_dimensions(self) -> "Settings":
        if self.tender_embedding_dimensions != 1536:
            raise ValueError("TENDER_EMBEDDING_DIMENSIONS must be 1536 for M3 mappings")
        return self

    @property
    def ingest_supported_extensions_set(self) -> set[str]:
        return {
            ext.strip().lower()
            for ext in self.ingest_supported_extensions.split(",")
            if ext.strip()
        }

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    def model_post_init(self, __context: object) -> None:
        os.environ.setdefault("OPENAI_API_KEY", self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
