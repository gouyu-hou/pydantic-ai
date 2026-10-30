"""The right-hand column: Monty and Changes replace each other instead of stacking."""

import re
from collections.abc import Iterator

import pytest
from anyio.from_thread import start_blocking_portal
from playwright.async_api import Page, expect

from pydantic_ai import Agent, models
from pydantic_ai.models.test import TestModel
from tests.clai2.browser.conftest import Serve
from tests.clai2.test_web import TOKEN
from tests.clai2.test_web_sessions import Fleet

CHANGES_TOGGLE = re.compile(r'^Changes')
"""The header's Changes button, whose name carries the changed-file count."""
MONTY_TOGGLE = re.compile(r'^(Show|Hide) Monty, the run_code sandbox')
MONTY_PANEL = 'Monty, the run_code sandbox'


@pytest.fixture(scope='module')
def panels_ui(tmp_path_factory: pytest.TempPathFactory, serve: Serve) -> Iterator[str]:
    """Serve one session whose agent never runs, so only the panels are under test."""
    root = tmp_path_factory.mktemp('browser-panels').resolve()
    with pytest.MonkeyPatch.context() as patch, start_blocking_portal() as portal:
        patch.setenv('HOME', str(root / 'home'))
        patch.setenv('XDG_CONFIG_HOME', str(root / 'config'))
        patch.setenv('XDG_STATE_HOME', str(root / 'state'))
        patch.setattr(models, 'ALLOW_MODEL_REQUESTS', False)
        fleet = Fleet(root=root, portal=portal, agents={'work': Agent(TestModel(call_tools=[]))})
        try:
            fleet.new('work')
            with serve(fleet) as url:
                yield url
        finally:
            fleet.exit()


async def test_monty_and_changes_replace_each_other(page: Page, panels_ui: str) -> None:
    await page.goto(f'{panels_ui}/?token={TOKEN}')
    app = page.locator('.app')
    changes = page.get_by_role('complementary', name='Changes')
    monty = page.get_by_role('complementary', name=MONTY_PANEL)
    changes_toggle = page.get_by_role('button', name=CHANGES_TOGGLE)
    monty_toggle = page.get_by_role('button', name=MONTY_TOGGLE)
    await expect(changes_toggle).to_be_enabled()

    await changes_toggle.click()
    await expect(changes).to_be_visible()

    # Both take the same column, so opening Monty closes Changes instead of squeezing the chat to half width.
    await monty_toggle.click()
    await expect(monty).to_be_visible()
    await expect(changes).to_have_count(0)
    await expect(app).to_have_class(re.compile(r'\bwith-monty\b'))
    await expect(app).not_to_have_class(re.compile(r'\bwith-side-panel\b'))

    # And back: Changes replaces Monty, so the column never holds two panels.
    await changes_toggle.click()
    await expect(changes).to_be_visible()
    await expect(monty).to_have_count(0)
    await expect(app).not_to_have_class(re.compile(r'\bwith-monty\b'))

    # The shortcut is the second way in, and takes the column from Changes the same way the button does.
    await page.keyboard.press('ControlOrMeta+J')
    await expect(monty).to_be_visible()
    await expect(changes).to_have_count(0)
    await expect(app).to_have_class(re.compile(r'\bwith-monty\b'))
