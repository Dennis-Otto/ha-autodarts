"""A camera alarm requires sustained zero FPS during active detection."""

import pytest

from custom_components.homedarts.camera_health import CameraHealth


def board(fps=None, running=True, status="Throw", cameras=True):
    """The data of a board with three cameras, and the readings of its cameras."""
    return (
        {
            "settings": {"camera_count": 3},
            "local": {"running": running, "status": status},
        },
        {
            "camera_state": {"isRunning": cameras},
            "camera_stats": {"fps": [30, 0, 30] if fps is None else fps},
        },
    )


def test_sustained_failure_grace_period_and_recovery():
    health = CameraHealth()
    assert health.update(*board(), 100) == [False, False, False]
    assert health.update(*board(), 114) == [False, False, False]
    assert health.update(*board(), 115) == [False, True, False]
    assert health.update(*board(fps=[30, 30, 30]), 116) == [False, False, False]
    assert health.update(*board(), 117) == [False, False, False]


@pytest.mark.parametrize(
    "changes",
    [
        {"running": False},
        {"status": "Calibrating"},
        {"status": "Starting"},
        {"cameras": False},
    ],
)
def test_normal_stop_calibration_and_standby_do_not_alarm(changes):
    health = CameraHealth()
    health.update(*board(), 100)
    assert health.update(*board(**changes), 130) == [False, False, False]
    assert health.update(*board(), 131) == [False, False, False]


def test_unknown_fps_is_not_zero_and_interrupts_failure_window():
    health = CameraHealth()
    health.update(*board(), 100)
    assert health.update(*board(fps=[30, None, 30]), 120) == [False, None, False]
    assert health.update(*board(), 121) == [False, False, False]
    assert health.update(*board(fps=[]), 122) == [None, None, None]
