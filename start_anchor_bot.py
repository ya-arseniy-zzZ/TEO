#!/usr/bin/env python3
"""
Simple script to start Anchor-UX Teo Bot
"""
import asyncio
import sys
import os
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.anchor_teo_bot import anchor_teo_bot

# Global flag for graceful shutdown
shutdown_flag = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    shutdown_flag = True

async def main():
    """Main function"""
    global shutdown_flag
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🚀 Starting Anchor-UX Teo Bot...")
        
        # Setup the bot
        await anchor_teo_bot.setup()
        await anchor_teo_bot.application.initialize()
        await anchor_teo_bot.application.start()
        
        print("✅ Bot is running! Press Ctrl+C to stop.")
        print("📱 You can now test the bot in Telegram by sending /start")
        
        # Start polling in a separate task
        polling_task = asyncio.create_task(
            anchor_teo_bot.application.run_polling(
                allowed_updates=anchor_teo_bot.application.bot.get_updates,
                close_loop=False,
                stop_signals=None
            )
        )
        
        # Wait for shutdown signal
        while not shutdown_flag:
            await asyncio.sleep(1)
        
        print("\n🛑 Shutting down bot...")
        
        # Cancel polling task
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        
        # Stop the bot
        await anchor_teo_bot.stop()
        
        print("✅ Bot stopped successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        try:
            await anchor_teo_bot.stop()
        except Exception as stop_error:
            print(f"❌ Error stopping bot: {stop_error}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)





