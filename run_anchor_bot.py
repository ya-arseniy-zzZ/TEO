#!/usr/bin/env python3
"""
Simple script to run Anchor-UX Teo Bot
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from src.core.anchor_teo_bot import anchor_teo_bot

async def main():
    """Main function"""
    try:
        print("Starting Anchor-UX Teo Bot...")
        await anchor_teo_bot.start()
    except KeyboardInterrupt:
        print("\nStopping bot...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            await anchor_teo_bot.stop()
        except Exception as e:
            print(f"Error stopping bot: {e}")
        print("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())




