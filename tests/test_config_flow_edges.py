"""Less common config-flow paths."""

from unittest.mock import patch

from homeassistant.data_entry_flow import FlowResultType

from .local_helpers import mock_board
from .test_local_flow import open_local


async def test_local_board_without_version_is_added(hass, aioclient_mock):
    mock_board(aioclient_mock, version="unknown")
    result = await open_local(hass)
    with patch("custom_components.autodarts.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.0.2.10", "port": 3180}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "api_generation" not in result["data"]
