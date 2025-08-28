#!/usr/bin/env python3
"""
Simple script to run Anchor-UX Teo Bot
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.anchor_teo_bot import anchor_teo_bot

async def main():
    """Main function"""
    try:
        print("🚀 Starting Anchor-UX Teo Bot...")
        
        # Setup the bot
        await anchor_teo_bot.setup()
        
        print("✅ Bot setup completed!")
        print("📱 Starting polling...")
        
        # Start the bot with polling
        await anchor_teo_bot.application.run_polling(
            allowed_updates=anchor_teo_bot.application.bot.get_updates,
            close_loop=False
        )
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        try:
            await anchor_teo_bot.stop()
        except Exception as stop_error:
            print(f"❌ Error stopping bot: {stop_error}")
    finally:
        print("✅ Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())





