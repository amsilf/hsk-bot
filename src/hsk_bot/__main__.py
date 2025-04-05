import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from .bot import HSKBot

def get_resources_path() -> Path:
    """Get the path to resources directory.
    
    Returns:
        Path to resources directory, preferring /app/resources in container
        and falling back to local path if not in container
    """
    # First try container path
    container_path = Path("/app/resources")
    if container_path.exists():
        return container_path
    
    # Fallback to local path
    local_path = Path(__file__).parent.parent.parent / "resources"
    if local_path.exists():
        return local_path
    
    raise FileNotFoundError(
        "Resources directory not found. Tried:\n"
        f"- Container path: {container_path}\n"
        f"- Local path: {local_path}"
    )

def main() -> None:
    """Main entry point for the HSK bot."""
    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting HSK Bot")

    # Load environment variables
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    # Get the path to vocabulary files
    try:
        vocab_path = get_resources_path()
        logger.info(f"Using vocabulary path: {vocab_path}")
    except FileNotFoundError as e:
        logger.error(str(e))
        raise

    # Create and run the bot
    logger.info("Initializing bot")
    bot = HSKBot(token=token, vocabulary_path=vocab_path)
    logger.info("Starting bot polling")
    bot.run()

if __name__ == "__main__":
    main() 