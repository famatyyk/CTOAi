import os


DEFAULT_DEV_JWT_PLACEHOLDER = "dev-jwt-placeholder-change-me"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    return os.getenv("CTOA_ENV", "").strip().lower() in {"prod", "production"}


def validate_early_security_config() -> None:
    if not _is_production_env():
        return

    origins = [
        origin.strip()
        for origin in os.getenv("CTOA_CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]
    if not origins or "*" in origins:
        raise RuntimeError(
            "CTOA_CORS_ORIGINS must be set to explicit origins in production"
        )

    secret = os.getenv("CTOA_JWT_SECRET", "").strip()
    if not secret or secret == DEFAULT_DEV_JWT_PLACEHOLDER:
        raise RuntimeError(
            "Refusing to start in production with missing or weak CTOA_JWT_SECRET."
        )

    if (
        _env_bool("CTOA_API_SELF_REGISTER_ENABLED", False)
        and not os.getenv("CTOA_API_SELF_REGISTER_CODE", "").strip()
    ):
        raise RuntimeError(
            "CTOA_API_SELF_REGISTER_CODE must be set when API self registration is enabled in production"
        )


validate_early_security_config()
