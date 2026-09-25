import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration import _align_screens_to_happy_path


def test_generated_screens_are_reordered_to_the_approved_happy_path():
    happy_path = [
        {"step": 1, "screen_name": "Start"},
        {"step": 2, "screen_name": "Application form"},
        {"step": 3, "screen_name": "Confirmation"},
    ]
    screens = [
        {"screen_name": "confirmation", "html": "<html>confirmation</html>"},
        {"screen_name": "START", "html": "<html>start</html>"},
    ]

    aligned, missing = _align_screens_to_happy_path(happy_path, screens)

    assert [screen["screen_name"] for screen in aligned] == ["Start", "Confirmation"]
    assert [step["screen_name"] for step in missing] == ["Application form"]


def test_invalid_or_unnamed_generation_does_not_count_as_a_happy_path_screen():
    happy_path = [{"step": 1, "screen_name": "Start"}]
    aligned, missing = _align_screens_to_happy_path(happy_path, [{"screen_name": "Start"}])

    assert aligned == []
    assert missing == happy_path
