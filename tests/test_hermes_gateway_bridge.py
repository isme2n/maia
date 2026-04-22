from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from maia.hermes_gateway_bridge import (
    GatewayOnboardingConfig,
    load_onboarding_config,
    patch_gateway_runner,
)


class FakePlatform:
    def __init__(self, value: str) -> None:
        self.value = value


class DummyLock:
    def __init__(self) -> None:
        self.entries = 0

    def __enter__(self) -> "DummyLock":
        self.entries += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class PrivateApprovePairingStore:
    def __init__(self) -> None:
        self._lock = DummyLock()
        self.approved: set[tuple[str, str]] = set()
        self.calls: list[tuple[str, ...]] = []

    def is_approved(self, platform: str, user_id: str) -> bool:
        self.calls.append(("is_approved", platform, user_id))
        return (platform, user_id) in self.approved

    def _approve_user(self, platform: str, user_id: str, user_name: str = "") -> None:
        self.calls.append(("_approve_user", platform, user_id, user_name))
        self.approved.add((platform, user_id))


class PublicApprovePairingStore:
    def __init__(self) -> None:
        self.approved: set[tuple[str, str]] = set()
        self.calls: list[tuple[str, ...]] = []

    def is_approved(self, platform: str, user_id: str) -> bool:
        self.calls.append(("is_approved", platform, user_id))
        return (platform, user_id) in self.approved

    def approve(self, platform: str, user_id: str, user_name: str = "") -> None:
        self.calls.append(("approve", platform, user_id, user_name))
        self.approved.add((platform, user_id))


class PublicApproveUserPairingStore:
    def __init__(self) -> None:
        self.approved: set[tuple[str, str]] = set()
        self.calls: list[tuple[str, ...]] = []

    def is_approved(self, platform: str, user_id: str) -> bool:
        self.calls.append(("is_approved", platform, user_id))
        return (platform, user_id) in self.approved

    def approve_user(self, user_id: str, platform: str, user_name: str = "") -> None:
        self.calls.append(("approve_user", platform, user_id, user_name))
        self.approved.add((platform, user_id))


def _platform_name(source: SimpleNamespace) -> str:
    platform = source.platform
    if isinstance(platform, str):
        return platform
    return platform.value


def _make_runner_class(pairing_store_type: type, *, authorize_from_pairing: bool) -> type:
    class FakeRunner:
        def __init__(self) -> None:
            self.pairing_store = pairing_store_type()
            self.auth_checks = 0

        def _is_user_authorized(self, source: SimpleNamespace) -> bool:
            self.auth_checks += 1
            if not authorize_from_pairing:
                return False
            return self.pairing_store.is_approved(_platform_name(source), source.user_id)

    return FakeRunner


def test_load_onboarding_config_defaults_to_self_serve_telegram() -> None:
    config = load_onboarding_config({})

    assert config.mode == "self_serve"
    assert config.self_serve_platforms == frozenset({"telegram"})
    assert config.self_serve_enabled is True


def test_load_onboarding_config_respects_env_overrides() -> None:
    config = load_onboarding_config(
        {
            "MAIA_GATEWAY_ONBOARDING_MODE": "strict",
            "MAIA_GATEWAY_SELF_SERVE_PLATFORMS": "telegram,slack",
        }
    )

    assert config.mode == "strict"
    assert config.self_serve_platforms == frozenset({"telegram", "slack"})
    assert config.self_serve_enabled is False


def test_patch_gateway_runner_self_serves_telegram_dm_with_private_approve() -> None:
    runner_class = _make_runner_class(PrivateApprovePairingStore, authorize_from_pairing=True)
    gateway_run = ModuleType("gateway.run")
    gateway_run.GatewayRunner = runner_class
    patch_gateway_runner(
        gateway_run,
        GatewayOnboardingConfig(
            mode="self_serve",
            self_serve_platforms=frozenset({"telegram"}),
        ),
    )
    runner = runner_class()
    source = SimpleNamespace(
        platform=FakePlatform("telegram"),
        chat_type="dm",
        user_id="user-123",
        user_name="Alice",
    )

    authorized = runner._is_user_authorized(source)

    assert authorized is True
    assert runner.auth_checks == 2
    assert runner.pairing_store.calls == [
        ("is_approved", "telegram", "user-123"),
        ("_approve_user", "telegram", "user-123", "Alice"),
        ("is_approved", "telegram", "user-123"),
    ]
    assert runner.pairing_store._lock.entries == 1


def test_patch_gateway_runner_supports_public_approve_and_enum_platform() -> None:
    runner_class = _make_runner_class(PublicApprovePairingStore, authorize_from_pairing=True)
    gateway_run = ModuleType("gateway.run")
    gateway_run.GatewayRunner = runner_class
    patch_gateway_runner(
        gateway_run,
        GatewayOnboardingConfig(
            mode="self_serve",
            self_serve_platforms=frozenset({"telegram"}),
        ),
    )
    runner = runner_class()
    source = SimpleNamespace(
        platform=FakePlatform("telegram"),
        chat_type="dm",
        user_id="user-321",
        user_name="Dana",
    )

    authorized = runner._is_user_authorized(source)

    assert authorized is True
    assert runner.pairing_store.calls == [
        ("is_approved", "telegram", "user-321"),
        ("approve", "telegram", "user-321", "Dana"),
        ("is_approved", "telegram", "user-321"),
    ]


def test_patch_gateway_runner_supports_public_approve_user_and_string_platform() -> None:
    runner_class = _make_runner_class(PublicApproveUserPairingStore, authorize_from_pairing=True)
    gateway_run = ModuleType("gateway.run")
    gateway_run.GatewayRunner = runner_class
    patch_gateway_runner(
        gateway_run,
        GatewayOnboardingConfig(
            mode="self_serve",
            self_serve_platforms=frozenset({"telegram"}),
        ),
    )
    runner = runner_class()
    source = SimpleNamespace(
        platform="telegram",
        chat_type="dm",
        user_id="user-456",
        user_name="Bob",
    )

    authorized = runner._is_user_authorized(source)

    assert authorized is True
    assert runner.pairing_store.calls == [
        ("is_approved", "telegram", "user-456"),
        ("approve_user", "telegram", "user-456", "Bob"),
        ("is_approved", "telegram", "user-456"),
    ]


def test_patch_gateway_runner_rechecks_original_auth_after_auto_approve() -> None:
    runner_class = _make_runner_class(PrivateApprovePairingStore, authorize_from_pairing=False)
    gateway_run = ModuleType("gateway.run")
    gateway_run.GatewayRunner = runner_class
    patch_gateway_runner(
        gateway_run,
        GatewayOnboardingConfig(
            mode="self_serve",
            self_serve_platforms=frozenset({"telegram"}),
        ),
    )
    runner = runner_class()
    source = SimpleNamespace(
        platform=FakePlatform("telegram"),
        chat_type="dm",
        user_id="user-789",
        user_name="Carol",
    )

    authorized = runner._is_user_authorized(source)

    assert authorized is False
    assert runner.auth_checks == 2
    assert ("_approve_user", "telegram", "user-789", "Carol") in runner.pairing_store.calls


@pytest.mark.parametrize(
    ("platform", "chat_type"),
    [
        ("discord", "dm"),
        ("telegram", "group"),
    ],
)
def test_patch_gateway_runner_limits_self_serve_to_configured_dm_sources(
    platform: str,
    chat_type: str,
) -> None:
    runner_class = _make_runner_class(PrivateApprovePairingStore, authorize_from_pairing=True)
    gateway_run = ModuleType("gateway.run")
    gateway_run.GatewayRunner = runner_class
    patch_gateway_runner(
        gateway_run,
        GatewayOnboardingConfig(
            mode="self_serve",
            self_serve_platforms=frozenset({"telegram"}),
        ),
    )
    runner = runner_class()
    source = SimpleNamespace(
        platform=FakePlatform(platform),
        chat_type=chat_type,
        user_id="user-000",
        user_name="Mallory",
    )

    authorized = runner._is_user_authorized(source)

    assert authorized is False
    assert runner.auth_checks == 1
    assert runner.pairing_store.calls == [("is_approved", platform, "user-000")]
