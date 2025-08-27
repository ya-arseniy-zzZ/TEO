"""
Main entry point for Anchor-UX Teo Bot
"""
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.anchor_teo_bot import anchor_teo_bot

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Main function"""
    try:
        logger.info("Starting Anchor-UX Teo Bot...")
        await anchor_teo_bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping bot...")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        try:
            await anchor_teo_bot.stop()
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
