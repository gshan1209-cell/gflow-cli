"""Real output-count controls, zero generation quota.

Needs GFLOW_CLI_E2E_PROFILE and GFLOW_CLI_E2E_PROJECT. Optional
GFLOW_CLI_E2E_COUNT_SCREENSHOT saves the selected settings pane locally.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_bdd import given, scenarios, then, when

from gflow_cli.api.client import FlowApiClient
from gflow_cli.api.transports.migrated_composer import RADIO, MigratedComposer
from gflow_cli.api.video import Aspect, GenerateVideoRequest, Mode, VideoModel
from gflow_cli.config import get_settings, reset_settings

scenarios("../features/migrated_count_spacing.feature")


@pytest.fixture
def count_world() -> dict[str, Any]:
    return {}


@given("a signed-in Flow project for count verification")
def signed_in_project(
    count_world: dict[str, Any], e2e_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    project = os.environ.get("GFLOW_CLI_E2E_PROJECT", "").strip()
    if not project:
        pytest.skip("Set GFLOW_CLI_E2E_PROJECT to an existing owned Flow project")
    if home := e2e_env.get("GFLOW_CLI_HOME"):
        monkeypatch.setenv("GFLOW_CLI_HOME", home)
    else:
        monkeypatch.delenv("GFLOW_CLI_HOME", raising=False)
    reset_settings()
    count_world["profile"] = get_settings().profile_subdir(e2e_env["GFLOW_CLI_PROFILE"])
    count_world["project"] = project


@when("one output is selected on the real settings pane")
def select_one(count_world: dict[str, Any]) -> None:
    async def drive() -> None:
        async with FlowApiClient(profile_dir=count_world["profile"], headless=False) as client:
            page = client._page  # noqa: SLF001 - real editor verification
            assert page is not None
            composer = MigratedComposer()
            assert await composer.ensure_editor(page, count_world["project"]) == "classic"
            request = GenerateVideoRequest(
                prompt="settings verification only",
                mode=Mode.T2V,
                aspect=Aspect.LANDSCAPE,
                model=VideoModel.VEO_3_1_LITE,
                count=1,
            )
            guard = AsyncMock(side_effect=AssertionError("Settings verification must not submit"))
            with patch.object(composer, "submit_and_observe", guard):
                await composer.apply_video_settings(page, request)
                pane = await composer._open_pane(page)  # noqa: SLF001 - inspect real readback
                selected = []
                for radio in await pane.locator(RADIO).all():
                    label = re.sub(r"\s+", "", await radio.inner_text())
                    if (
                        re.fullmatch(r"x\d+", label)
                        and await radio.get_attribute("aria-checked") == "true"
                    ):
                        selected.append(label)
                if screenshot := os.environ.get("GFLOW_CLI_E2E_COUNT_SCREENSHOT"):
                    await page.screenshot(path=str(Path(screenshot)))
                await composer._close_pane(page, strict=True)  # noqa: SLF001
                guard.assert_not_awaited()
            count_world["selected"] = selected
            count_world["submissions"] = guard.await_count

    asyncio.run(drive())


@then("only one output is checked and no generation is submitted")
def verify_one(count_world: dict[str, Any]) -> None:
    assert count_world["selected"] == ["x1"]
    assert count_world["submissions"] == 0
