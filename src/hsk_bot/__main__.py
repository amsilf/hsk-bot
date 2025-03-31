import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from .bot import HSKBot

def main() -> None:
    """Main entry point for the HSK bot."""
    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Load environment variables
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    # Get the path to vocabulary files
    vocab_path = Path(__file__).parent.parent.parent / "resources"
    
    # Create and run the bot
    bot = HSKBot(token=token, vocabulary_path=vocab_path)
    bot.run()

if __name__ == "__main__":
    main() 