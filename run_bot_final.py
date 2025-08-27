#!/usr/bin/env python3
"""
Final script to run Anchor-UX Teo Bot
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
        
        # Simple polling loop without run_polling
        offset = 0
        while not shutdown_flag:
            try:
                # Get updates
                updates = await anchor_teo_bot.application.bot.get_updates(
                    offset=offset,
                    timeout=30
                )
                
                # Process updates
                for update in updates:
                    offset = update.update_id + 1
                    await anchor_teo_bot.application.process_update(update)
                
                # Small delay
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Update error: {e}")
                await asyncio.sleep(5)  # Wait longer on error
        
        print("\n🛑 Shutting down bot...")
        
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





