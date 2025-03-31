from typing import TYPE_CHECKING
import pytest
from pathlib import Path
from hsk_bot.game import VocabularyGame
from hsk_bot.models import PracticeMode, Word

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

@pytest.fixture
def game(tmp_path: Path) -> VocabularyGame:
    """Create a VocabularyGame instance with test data."""
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    
    # Create test CSV file
    test_csv = vocab_dir / "hsk-1.csv"
    test_csv.write_text(
        "n,chinese,pinyin,english\n"
        "1,回,huí,return\n"
        "2,去,qù,go\n"
    )
    
    return VocabularyGame(vocab_dir)

def test_load_vocabulary(game: VocabularyGame) -> None:
    """Test vocabulary loading."""
    vocab = game.load_vocabulary(1)
    assert len(vocab) == 2
    assert vocab[0].chinese == "回"
    assert vocab[0].english == "return"

    with pytest.raises(ValueError):
        game.load_vocabulary(7)

def test_start_session(game: VocabularyGame) -> None:
    """Test session creation."""
    session = game.start_session(
        user_id=123456,
        hsk_level=1,
        mode=PracticeMode.CHINESE_TO_ENGLISH
    )
    
    assert session.user_state.user_id == 123456
    assert session.user_state.hsk_level == 1
    assert len(session.vocabulary) == 2

def test_check_answer(game: VocabularyGame) -> None:
    """Test answer checking functionality."""
    session = game.start_session(
        user_id=123456,
        hsk_level=1,
        mode=PracticeMode.CHINESE_TO_ENGLISH
    )
    
    # Set current word manually for testing
    word = Word(chinese="回", pinyin="huí", english="return", hsk_level=1)
    session.user_state.current_word = word
    
    # Test correct answer
    assert game.check_answer(123456, "return")
    assert session.user_state.score == 1
    assert session.user_state.accuracy == 100.0
    
    # Test incorrect answer
    assert not game.check_answer(123456, "wrong")
    assert session.user_state.score == 1
    assert session.user_state.accuracy == 50.0 