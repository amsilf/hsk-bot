from pathlib import Path
import logging
from typing import Optional, cast

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from .game import VocabularyGame
from .models import PracticeMode

logger = logging.getLogger(__name__)

class HSKBot:
    """Telegram bot for HSK vocabulary practice.
    
    This class handles all bot commands and user interactions.
    """
    
    def __init__(self, token: str, vocabulary_path: Path) -> None:
        """Initialize the HSK bot.
        
        Args:
            token: Telegram bot token
            vocabulary_path: Path to vocabulary files
        """
        self.game = VocabularyGame(vocabulary_path)
        self.application = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up command and callback handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_answer))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command.
        
        Shows HSK level selection keyboard.
        """
        keyboard = [
            [
                InlineKeyboardButton(f"HSK {i}", callback_data=f"level_{i}")
                for i in range(1, 4)
            ],
            [
                InlineKeyboardButton(f"HSK {i}", callback_data=f"level_{i}")
                for i in range(4, 7)
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Welcome to HSK Vocabulary Practice! Please select your HSK level:",
            reply_markup=reply_markup
        )

    async def show_mode_selection(self, update: Update) -> None:
        """Show practice mode selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Pinyin → English", 
                    callback_data="mode_pinyin_to_english"
                )
            ],
            [
                InlineKeyboardButton(
                    "Characters → English", 
                    callback_data="mode_characters_to_english"
                )
            ],
            [
                InlineKeyboardButton(
                    "English → Characters", 
                    callback_data="mode_english_to_characters"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(
            "Select practice mode:",
            reply_markup=reply_markup
        )

    async def start_practice(self, update: Update, user_id: int, hsk_level: int, mode: PracticeMode) -> None:
        """Start practice session and show first word."""
        session = self.game.start_session(user_id, hsk_level, mode)
        word = self.game.get_next_word(user_id)
        
        if not word:
            await update.callback_query.message.reply_text(
                "Error loading vocabulary. Please try again."
            )
            return

        # Show the correct format based on practice mode
        if mode == PracticeMode.PINYIN_TO_ENGLISH:
            shown_word = word.pinyin
        elif mode == PracticeMode.CHARACTERS_TO_ENGLISH:
            shown_word = word.chinese
        else:  # ENGLISH_TO_CHARACTERS
            shown_word = word.english

        prompt = f"Translate this word: {shown_word}"
        await update.callback_query.message.reply_text(prompt)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id

        if data.startswith("level_"):
            level = int(data.split("_")[1])
            context.user_data["hsk_level"] = level
            await self.show_mode_selection(update)
            
        elif data.startswith("mode_"):
            mode_str = data.replace("mode_", "")
            mode = PracticeMode(mode_str)
            level = context.user_data.get("hsk_level", 1)
            await self.start_practice(update, user_id, level, mode)

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle user answers."""
        user_id = update.effective_user.id
        answer = update.message.text.strip()

        try:
            session = self.game.active_sessions.get(user_id)
            if not session:
                await update.message.reply_text(
                    "No active session. Use /start to begin practice."
                )
                return

            current_word = session.user_state.current_word
            if not current_word:
                await update.message.reply_text(
                    "No current word. Please start a new session with /start"
                )
                return

            is_correct = self.game.check_answer(user_id, answer)
            
            # Show the correct format in feedback
            mode = session.user_state.practice_mode
            if mode == PracticeMode.PINYIN_TO_ENGLISH:
                correct_answer = current_word.english
                next_shown_word = current_word.pinyin
                feedback_extra = f"\nChinese: {current_word.chinese}"
            elif mode == PracticeMode.CHARACTERS_TO_ENGLISH:
                correct_answer = current_word.english
                next_shown_word = current_word.chinese
                feedback_extra = f"\nPinyin: {current_word.pinyin}"
            else:  # ENGLISH_TO_CHARACTERS
                correct_answer = current_word.chinese
                next_shown_word = current_word.english
                feedback_extra = f"\nPinyin: {current_word.pinyin}"

            feedback = "✅ Correct!" if is_correct else f"❌ Incorrect! The correct answer was: {correct_answer}"
            feedback += feedback_extra
                
            await update.message.reply_text(feedback)
            
            # Show next word
            next_word = self.game.get_next_word(user_id)
            if next_word:
                if mode == PracticeMode.PINYIN_TO_ENGLISH:
                    shown_word = next_word.pinyin
                elif mode == PracticeMode.CHARACTERS_TO_ENGLISH:
                    shown_word = next_word.chinese
                else:  # ENGLISH_TO_CHARACTERS
                    shown_word = next_word.english
                    
                prompt = f"Next word: {shown_word}"
                await update.message.reply_text(prompt)
                
        except ValueError as e:
            await update.message.reply_text(str(e))

    def run(self) -> None:
        """Start the bot."""
        self.application.run_polling()
