from pathlib import Path
from typing import Optional
import pandas as pd
import random
import time

from .models import Word, UserState, GameSession, PracticeMode


class VocabularyGame:
    """Manages the HSK vocabulary learning game logic.
    
    This class handles loading vocabulary, managing game sessions,
    and checking user answers.
    """
    
    def __init__(self, vocabulary_path: Path) -> None:
        """Initialize the vocabulary game.
        
        Args:
            vocabulary_path: Path to the directory containing HSK CSV files
        """
        self.vocabulary_path = vocabulary_path
        self.active_sessions: dict[int, GameSession] = {}

    def load_vocabulary(self, hsk_level: int) -> list[Word]:
        """Load vocabulary for the specified HSK level.
        
        Args:
            hsk_level: HSK level (1-6)
            
        Returns:
            List of Word objects for the specified level
            
        Raises:
            FileNotFoundError: If vocabulary file doesn't exist
            ValueError: If HSK level is invalid
        """
        if not 1 <= hsk_level <= 6:
            raise ValueError(f"Invalid HSK level: {hsk_level}")
            
        file_path = self.vocabulary_path / f"hsk-{hsk_level}.csv"
        df = pd.read_csv(file_path)
        
        return [
            Word(
                chinese=row['chinese'],
                pinyin=row['pinyin'],
                english=row['english'],
                hsk_level=hsk_level
            )
            for _, row in df.iterrows()
        ]

    def start_session(self, user_id: int, hsk_level: int, mode: PracticeMode) -> GameSession:
        """Start a new learning session for a user.
        
        Args:
            user_id: Telegram user ID
            hsk_level: Selected HSK level
            mode: Selected practice mode
            
        Returns:
            New GameSession instance
        """
        user_state = UserState(
            user_id=user_id,
            hsk_level=hsk_level,
            practice_mode=mode
        )
        
        vocabulary = self.load_vocabulary(hsk_level)
        session = GameSession(
            user_state=user_state,
            vocabulary=vocabulary,
            start_time=time.time()
        )
        
        self.active_sessions[user_id] = session
        return session

    def get_next_word(self, user_id: int) -> Optional[Word]:
        """Get the next random word for the user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Random Word object or None if no session exists
        """
        session = self.active_sessions.get(user_id)
        if not session or not session.vocabulary:
            return None
            
        word = random.choice(session.vocabulary)
        session.user_state.current_word = word
        return word

    def check_answer(self, user_id: int, answer: str) -> bool:
        """Check if the user's answer is correct.
        
        Args:
            user_id: Telegram user ID
            answer: User's answer
            
        Returns:
            True if answer is correct, False otherwise
            
        Raises:
            ValueError: If no active session or current word exists
        """
        session = self.active_sessions.get(user_id)
        if not session or not session.user_state.current_word:
            raise ValueError("No active session or current word")
            
        current_word = session.user_state.current_word
        expected = (
            current_word.english.lower()
            if session.user_state.practice_mode == PracticeMode.CHINESE_TO_ENGLISH
            else current_word.chinese
        )
        
        is_correct = answer.lower().strip() == expected.lower().strip()
        
        # Update statistics
        session.user_state.total_attempts += 1
        if is_correct:
            session.user_state.correct_attempts += 1
            session.user_state.score += 1
            
        return is_correct

    def end_session(self, user_id: int) -> Optional[UserState]:
        """End the user's learning session.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Final UserState or None if no session exists
        """
        session = self.active_sessions.pop(user_id, None)
        return session.user_state if session else None
