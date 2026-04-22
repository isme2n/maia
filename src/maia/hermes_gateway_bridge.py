"""Maia patch layer for Hermes gateway self-serve onboarding."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from dataclasses import dataclass, field
import importlib
import inspect
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

__all__ = [
    "GatewayOnboardingConfig",
    "load_onboarding_config",
    "main",
    "patch_gateway_runner",
]

_DEFAULT_SELF_SERVE_PLATFORMS = frozenset({"telegram"})
_USER_ID_PARAM_NAMES = frozenset({"user", "user_id", "uid"})
_USER_NAME_PARAM_NAMES = frozenset({"name", "user_name", "username"})


class _UnsupportedApprovalMethod(TypeError):
    """Raised when a PairingStore approval method is not user-approval compatible."""


@dataclass(slots=True)
class GatewayOnboardingConfig:
    mode: str = "self_serve"
    self_serve_platforms: frozenset[str] = field(
        default_factory=lambda: _DEFAULT_SELF_SERVE_PLATFORMS
    )

    @property
    def self_serve_enabled(self) -> bool:
        return self.mode == "self_serve" and bool(self.self_serve_platforms)


def load_onboarding_config(env: dict[str, str] | None = None) -> GatewayOnboardingConfig:
    source = os.environ if env is None else env
    mode = source.get("MAIA_GATEWAY_ONBOARDING_MODE", "self_serve").strip().lower()
    raw_platforms = source.get("MAIA_GATEWAY_SELF_SERVE_PLATFORMS", "telegram")
    platforms = frozenset(
        part.strip().lower() for part in raw_platforms.split(",") if part.strip()
    )
    return GatewayOnboardingConfig(
        mode=mode or "self_serve",
        self_serve_platforms=platforms or _DEFAULT_SELF_SERVE_PLATFORMS,
    )


def patch_gateway_runner(
    gateway_run: ModuleType,
    config: GatewayOnboardingConfig | None = None,
) -> None:
    onboarding = load_onboarding_config() if config is None else config
    runner_class = gateway_run.GatewayRunner
    original = getattr(
        runner_class,
        "__maia_original_is_user_authorized__",
        runner_class._is_user_authorized,
    )
    runner_class.__maia_original_is_user_authorized__ = original

    def _patched_is_user_authorized(self: Any, source: Any) -> bool:
        if original(self, source):
            return True
        if not onboarding.self_serve_enabled or not _is_self_serve_candidate(source, onboarding):
            return False
        pairing_store = getattr(self, "pairing_store", None)
        if pairing_store is None:
            return False
        try:
            _approve_user(pairing_store, source)
        except Exception:
            return False
        return bool(original(self, source))

    runner_class._is_user_authorized = _patched_is_user_authorized


def main() -> int:
    gateway_run = _load_gateway_run_module()
    patch_gateway_runner(gateway_run)
    result = gateway_run.start_gateway()
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    return 0 if result else 1


def _load_gateway_run_module() -> ModuleType:
    try:
        return importlib.import_module("gateway.run")
    except ModuleNotFoundError:
        _maybe_add_default_gateway_root()
        return importlib.import_module("gateway.run")


def _maybe_add_default_gateway_root() -> None:
    configured_root = os.environ.get("MAIA_HERMES_GATEWAY_ROOT", "").strip()
    candidates = [configured_root] if configured_root else []
    candidates.append(str(Path.home() / ".hermes" / "hermes-agent"))
    for candidate in candidates:
        if not candidate:
            continue
        if not Path(candidate).exists():
            continue
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
        return


def _is_self_serve_candidate(
    source: Any,
    config: GatewayOnboardingConfig,
) -> bool:
    if getattr(source, "chat_type", "") != "dm":
        return False
    if not getattr(source, "user_id", None):
        return False
    return _normalize_platform(getattr(source, "platform", None)) in config.self_serve_platforms


def _approve_user(pairing_store: Any, source: Any) -> None:
    platform = _normalize_platform(getattr(source, "platform", None))
    user_id = str(getattr(source, "user_id", "") or "").strip()
    user_name = str(getattr(source, "user_name", "") or "")
    if not platform or not user_id:
        raise ValueError("Gateway self-serve approval requires platform and user_id")

    for method_name in ("approve", "approve_user"):
        method = getattr(pairing_store, method_name, None)
        if callable(method):
            try:
                _invoke_approval_method(
                    method,
                    platform=platform,
                    user_id=user_id,
                    user_name=user_name,
                )
                return
            except _UnsupportedApprovalMethod:
                continue

    private_method = getattr(pairing_store, "_approve_user", None)
    if not callable(private_method):
        raise AttributeError("PairingStore approval method not found")

    lock = getattr(pairing_store, "_lock", None)
    context = lock if hasattr(lock, "__enter__") else nullcontext()
    with context:
        _invoke_approval_method(
            private_method,
            platform=platform,
            user_id=user_id,
            user_name=user_name,
        )


def _invoke_approval_method(
    method: Any,
    *,
    platform: str,
    user_id: str,
    user_name: str,
) -> None:
    signature = inspect.signature(method)
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    saw_user_id = False

    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            continue
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            continue

        if parameter.name == "platform":
            target = platform
        elif parameter.name in _USER_ID_PARAM_NAMES:
            target = user_id
            saw_user_id = True
        elif parameter.name in _USER_NAME_PARAM_NAMES:
            target = user_name
        elif parameter.default is not inspect.Signature.empty:
            continue
        else:
            raise _UnsupportedApprovalMethod(
                f"Unsupported approval method signature for {getattr(method, '__name__', 'approve')}"
            )

        if parameter.kind is inspect.Parameter.KEYWORD_ONLY:
            kwargs[parameter.name] = target
        else:
            args.append(target)

    if not saw_user_id:
        raise _UnsupportedApprovalMethod(
            f"Approval method {getattr(method, '__name__', 'approve')} does not accept a user id"
        )

    method(*args, **kwargs)


def _normalize_platform(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value.strip().lower()
    enum_name = getattr(value, "name", None)
    if isinstance(enum_name, str):
        return enum_name.strip().lower()
    return str(value).strip().lower()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
