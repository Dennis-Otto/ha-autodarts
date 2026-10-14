"""Turns down every setup of Radio Browser in the Home Assistant of the tests."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class LeftOut(ConfigFlow, domain="radio_browser"):
    """Onboarding and the button "Add integration" get no entry, so nothing looks up
    radio stations on the internet."""

    VERSION = 1

    async def async_step_onboarding(
        self, data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The step that onboarding starts for its default integrations."""
        return self.async_abort(reason="left_out")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The step of "Add integration", for whoever tries it in the demo."""
        return self.async_abort(reason="left_out")
