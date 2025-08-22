#!/usr/bin/env python3
"""
Teo Personal Assistant Bot - Entry Point
Run this file to start your bot
"""
import sys
import logging
from teo_bot import TeoBot

def main():
    """Main entry point for the bot"""
    try:
        bot = TeoBot()
        bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Error running bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()


