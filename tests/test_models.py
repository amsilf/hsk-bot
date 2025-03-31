from typing import TYPE_CHECKING
import pytest
from hsk_bot.models import Word, UserState, PracticeMode, GameSession

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

def test_word_validation() -> None:
    """Test Word model validation."""
    # Test valid word creation
    word = Word(
        chinese="回",
        pinyin="huí",
        english="return",
        hsk_level=1
    )
    assert word.chinese == "回"
    assert word.pinyin == "huí"
    assert word.english == "return"
    assert word.hsk_level == 1

    # Test invalid HSK level
    with pytest.raises(ValueError):
        Word(
            chinese="回",
            pinyin="huí",
            english="return",
            hsk_level=7
        )

def test_user_state() -> None:
    """Test UserState model functionality."""
    state = UserState(
        user_id=123456,
        hsk_level=1,
        practice_mode=PracticeMode.CHINESE_TO_ENGLISH
    )
    
    # Test initial values
    assert state.score == 0
    assert state.total_attempts == 0
    assert state.correct_attempts == 0
    assert state.accuracy == 0.0

    # Test accuracy calculation
    state.total_attempts = 10
    state.correct_attempts = 7
    assert state.accuracy == 70.0 