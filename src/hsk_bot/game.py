from pathlib import Path
from typing import Optional
import pandas as pd
import random
import time
import logging

from .models import Word, UserState, GameSession, PracticeMode

logger = logging.getLogger(__name__)


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
        logger.info(f"Loading vocabulary for HSK level {hsk_level}")
        
        if not 1 <= hsk_level <= 6:
            logger.error(f"Invalid HSK level requested: {hsk_level}")
            raise ValueError(f"Invalid HSK level: {hsk_level}")
            
        file_path = self.vocabulary_path / f"hsk-{hsk_level}.csv"
        logger.info(f"Attempting to load vocabulary from: {file_path}")
        
        # Read CSV with pipe separator
        try:
            df = pd.read_csv(
                file_path,
                sep='|',  # Use pipe as separator
                encoding='utf-8',
                dtype=str,  # Read all columns as strings
                on_bad_lines='warn'  # Warn about problematic lines instead of failing
            )
            logger.info(f"Successfully loaded CSV with {len(df)} entries")
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            raise
        
        # Convert column names to lowercase for case-insensitive matching
        df.columns = df.columns.str.lower()
        
        # Ensure we have the required columns
        required_columns = ['chinese', 'pinyin', 'english', 'part_of_speech']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns in CSV: {missing_columns}")
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        words = []
        for _, row in df.iterrows():
            try:
                word = Word(
                    chinese=str(row['chinese']).strip(),
                    pinyin=str(row['pinyin']).strip(),
                    english=str(row['english']).strip(),
                    part_of_speech=str(row['part_of_speech']).strip(),
                    hsk_level=hsk_level
                )
                words.append(word)
            except Exception as e:
                logger.warning(f"Skipping invalid row: {row} due to error: {e}")
        
        logger.info(f"Successfully loaded {len(words)} words for HSK level {hsk_level}")
        return words

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

    def _generate_word_variations(self, word: Word) -> set[str]:
        """Generate possible variations of a word based on its part of speech.
        
        Args:
            word: Word object containing the word and its part of speech
            
        Returns:
            Set of possible variations of the word
        """
        variations = set()
        
        # Split English translations and clean each part
        for translation in word.english.lower().split(','):
            translation = translation.strip()
            variations.add(translation)
            
            # Add individual words from the phrase
            words = translation.split()
            variations.update(words)
            
            # Based on part of speech, add common variations
            pos = word.part_of_speech.lower()
            
            if pos == 'verb':
                # Handle verb variations
                if translation.startswith('to '):
                    # If it starts with 'to', add version without 'to'
                    variations.add(translation.replace('to ', '', 1))
                else:
                    # If it doesn't start with 'to', add version with 'to'
                    variations.add(f"to {translation}")
                    
            elif pos == 'noun':
                # Handle noun variations with articles
                for article in ['a', 'an', 'the']:
                    variations.add(f"{article} {translation}")
                # Handle plural forms (basic -s rule)
                if not translation.endswith('s'):
                    variations.add(f"{translation}s")
                    
            elif pos == 'measure word':
                # Handle measure word variations
                variations.add(translation.replace('measure word', '').strip())
                variations.add(translation.replace('a measure word', '').strip())
                variations.add(translation.replace('for', '').strip())
                
        return variations

    def check_answer(self, user_id: int, answer: str) -> bool:
        """Check if the user's answer is correct.
        
        Handles variations based on part of speech:
        - Verbs: accepts with or without 'to'
        - Nouns: accepts with or without articles
        - Measure words: accepts variations of the description
        
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
        user_answer = answer.lower().strip()
        
        mode = session.user_state.practice_mode
        if mode in [PracticeMode.PINYIN_TO_ENGLISH, PracticeMode.CHARACTERS_TO_ENGLISH]:
            # Get all possible variations of the correct answer
            expected_variations = self._generate_word_variations(current_word)
            
            # Check if user's answer matches any variation
            is_correct = user_answer in expected_variations
            
            # If not exact match, try more flexible matching
            if not is_correct:
                # Remove articles from user's answer and try again
                user_answer_no_articles = ' '.join(
                    word for word in user_answer.split() 
                    if word not in ['a', 'an', 'the', 'to']
                ).strip()
                is_correct = user_answer_no_articles in expected_variations
                
        else:  # ENGLISH_TO_CHARACTERS
            # For Chinese character answers, exact match required
            is_correct = user_answer == current_word.chinese.strip()
        
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
