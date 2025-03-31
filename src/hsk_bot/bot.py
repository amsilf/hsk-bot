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
                InlineKeyboardButton("Chinese → English", callback_data="mode_chinese"),
                InlineKeyboardButton("English → Chinese", callback_data="mode_english"),
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

        prompt = (
            f"Translate this word: {word.chinese}"
            if mode == PracticeMode.CHINESE_TO_ENGLISH
            else f"Translate this word: {word.english}"
        )
        
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
            mode = PracticeMode.CHINESE_TO_ENGLISH if data == "mode_chinese" else PracticeMode.ENGLISH_TO_CHINESE
            level = context.user_data.get("hsk_level", 1)
            await self.start_practice(update, user_id, level, mode)

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle user answers."""
        user_id = update.effective_user.id
        answer = update.message.text

        try:
            is_correct = self.game.check_answer(user_id, answer)
            session = self.game.active_sessions.get(user_id)
            
            if not session:
                await update.message.reply_text(
                    "No active session. Use /start to begin practice."
                )
                return

            feedback = "✅ Correct!" if is_correct else "❌ Incorrect!"
            current_word = session.user_state.current_word
            if current_word:
                feedback += f"\nPinyin: {current_word.pinyin}"
                
            await update.message.reply_text(feedback)
            
            # Show next word
            next_word = self.game.get_next_word(user_id)
            if next_word:
                prompt = (
                    f"Next word: {next_word.chinese}"
                    if session.user_state.practice_mode == PracticeMode.CHINESE_TO_ENGLISH
                    else f"Next word: {next_word.english}"
                )
                await update.message.reply_text(prompt)
                
        except ValueError as e:
            await update.message.reply_text(str(e))

    def run(self) -> None:
        """Start the bot."""
        self.application.run_polling()
