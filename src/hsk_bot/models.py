from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PracticeMode(str, Enum):
    """Enum for practice modes.
    
    Attributes:
        CHINESE_TO_ENGLISH: Practice translating Chinese to English
        ENGLISH_TO_CHINESE: Practice translating English to Chinese
    """
    CHINESE_TO_ENGLISH = "chinese"
    ENGLISH_TO_CHINESE = "english"


class Word(BaseModel):
    """Represents a vocabulary word with its translations and metadata.
    
    Attributes:
        chinese: The Chinese character(s)
        pinyin: The pinyin romanization
        english: The English translation
        hsk_level: The HSK level (1-6)
    """
    chinese: str = Field(..., description="Chinese character(s)")
    pinyin: str = Field(..., description="Pinyin romanization")
    english: str = Field(..., description="English translation")
    hsk_level: int = Field(..., ge=1, le=6, description="HSK level (1-6)")


class UserState(BaseModel):
    """Represents the current state of a user's learning session.
    
    Attributes:
        user_id: Telegram user ID
        hsk_level: Selected HSK level
        practice_mode: Selected practice mode
        current_word: Currently active word for practice
        score: Current session score
        total_attempts: Total number of attempts in current session
        correct_attempts: Number of correct attempts in current session
    """
    user_id: int = Field(..., description="Telegram user ID")
    hsk_level: int = Field(..., ge=1, le=6, description="Selected HSK level")
    practice_mode: PracticeMode = Field(..., description="Selected practice mode")
    current_word: Optional[Word] = Field(None, description="Currently active word")
    score: int = Field(default=0, description="Current session score")
    total_attempts: int = Field(default=0, description="Total number of attempts")
    correct_attempts: int = Field(default=0, description="Number of correct attempts")

    @property
    def accuracy(self) -> float:
        """Calculate the current accuracy rate.
        
        Returns:
            float: Accuracy percentage (0-100)
        """
        if self.total_attempts == 0:
            return 0.0
        return (self.correct_attempts / self.total_attempts) * 100


class GameSession(BaseModel):
    """Represents an active learning session.
    
    Attributes:
        user_state: Current user state
        vocabulary: List of available words for practice
        start_time: Session start timestamp
    """
    user_state: UserState
    vocabulary: list[Word] = Field(default_factory=list)
    start_time: float = Field(..., description="Session start timestamp")
