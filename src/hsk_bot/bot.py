from pathlib import Path
import logging
from typing import Optional, cast

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
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

    END_SESSION_COMMAND = "🔚 End Session"

    async def show_word_with_end_button(self, message: str, chat_id: int) -> None:
        """Show a word with the End Session button.
        
        Args:
            message: The message to show
            chat_id: The chat ID to send the message to
        """
        # Create an inline keyboard with the End Session button
        keyboard = [[InlineKeyboardButton("🔚 End Session", callback_data="end_session")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup
            )
            logger.info("Message sent successfully with inline keyboard")
        except Exception as e:
            logger.error(f"Error sending message with keyboard: {e}")
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message
            )

    async def end_session(self, update: Update, user_id: int) -> None:
        """End the current session and show statistics.
        
        Args:
            update: The update object
            user_id: The user's ID
        """
        session = self.game.active_sessions.get(user_id)
        if not session:
            message = "No active session to end."
            if update.callback_query:
                await update.callback_query.message.reply_text(message)
            else:
                await update.message.reply_text(message)
            return

        # Get final statistics
        state = session.user_state
        accuracy = round(state.accuracy, 1)
        
        # End the session
        self.game.end_session(user_id)
        
        # Show final statistics
        stats_message = (
            f"Session ended!\n\n"
            f"Final Score: {state.score}\n"
            f"Total Attempts: {state.total_attempts}\n"
            f"Correct Answers: {state.correct_attempts}\n"
            f"Accuracy: {accuracy}%\n\n"
            f"Use /start to begin a new session!"
        )
        
        # Send the message based on update type
        if update.callback_query:
            await update.callback_query.message.reply_text(stats_message)
        else:
            await update.message.reply_text(stats_message)

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
        
        # Show the word with the End Session button
        await self.show_word_with_end_button(
            prompt,
            update.callback_query.message.chat_id
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()  # Answer the callback query
        
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
        
        elif data == "end_session":
            # Remove the inline keyboard from the message
            await query.message.edit_reply_markup(reply_markup=None)
            # End the session
            await self.end_session(update, user_id)

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
                feedback_extra = f"\nChinese: {current_word.chinese}"
            elif mode == PracticeMode.CHARACTERS_TO_ENGLISH:
                correct_answer = current_word.english
                feedback_extra = f"\nPinyin: {current_word.pinyin}"
            else:  # ENGLISH_TO_CHARACTERS
                correct_answer = current_word.chinese
                feedback_extra = f"\nPinyin: {current_word.pinyin}"

            feedback = "✅ Correct!" if is_correct else f"❌ Incorrect! The correct answer was: {correct_answer}"
            feedback += feedback_extra
                
            await update.message.reply_text(feedback)
            
            # Show next word with End Session button
            next_word = self.game.get_next_word(user_id)
            if next_word:
                if mode == PracticeMode.PINYIN_TO_ENGLISH:
                    shown_word = next_word.pinyin
                elif mode == PracticeMode.CHARACTERS_TO_ENGLISH:
                    shown_word = next_word.chinese
                else:  # ENGLISH_TO_CHARACTERS
                    shown_word = next_word.english
                    
                prompt = f"Next word: {shown_word}"
                await self.show_word_with_end_button(prompt, update.message.chat_id)
                
        except ValueError as e:
            await update.message.reply_text(str(e))

    def run(self) -> None:
        """Start the bot."""
        self.application.run_polling()
