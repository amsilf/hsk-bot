from typing import TYPE_CHECKING, AsyncGenerator
import pytest
from pathlib import Path
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes, Application, CallbackContext
from hsk_bot.bot import HSKBot
from hsk_bot.models import PracticeMode

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Add pytest-asyncio marker configuration
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture
def bot(tmp_path: Path) -> HSKBot:
    """Create a HSKBot instance with test data."""
    # Create test vocabulary file
    vocab_dir = tmp_path
    test_csv = vocab_dir / "hsk-1.csv"
    test_csv.write_text(
        "n,chinese,pinyin,english\n"
        "1,回,huí,return\n"
        "2,去,qù,go\n"
    )
    return HSKBot("test_token", vocab_dir)

@pytest.fixture
def mock_update(mocker: "MockerFixture") -> Update:
    """Create a mock Update object."""
    update = mocker.create_autospec(Update)
    message = mocker.create_autospec(Message)
    chat = mocker.create_autospec(Chat)
    user = mocker.create_autospec(User)
    
    update.message = message
    update.effective_user = user
    message.chat = chat
    user.id = 123456
    
    return update

@pytest.fixture
async def application() -> AsyncGenerator[Application, None]:
    """Create a real Application instance for testing."""
    app = Application.builder().token("test_token").build()
    yield app
    await app.shutdown()

@pytest.fixture
def context(application: Application) -> ContextTypes.DEFAULT_TYPE:
    """Create a Context object for testing."""
    return CallbackContext(application)

@pytest.mark.asyncio
async def test_start_command(
    bot: HSKBot,
    mock_update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Test the /start command."""
    await bot.start_command(mock_update, context)
    mock_update.message.reply_text.assert_called_once()
    args = mock_update.message.reply_text.call_args
    assert "Welcome to HSK Vocabulary Practice" in args[0][0]

@pytest.mark.asyncio
async def test_handle_answer(
    bot: HSKBot,
    mock_update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Test answer handling."""
    # Start a session first
    bot.game.start_session(123456, 1, PracticeMode.CHINESE_TO_ENGLISH)
    mock_update.message.text = "return"
    
    await bot.handle_answer(mock_update, context)
    mock_update.message.reply_text.assert_called() 