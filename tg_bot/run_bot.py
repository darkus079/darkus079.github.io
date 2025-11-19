#!/usr/bin/env python3
"""
Script to run the Telegram bot with proper PYTHONPATH setup.
"""

import sys
import os
import subprocess

# Add project root (parent of tg_bot) and src directory to Python path
project_root = os.path.dirname(os.path.dirname(__file__))  # Go up one level from tg_bot
tg_bot_path = os.path.dirname(__file__)
src_path = os.path.join(tg_bot_path, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, tg_bot_path)
sys.path.insert(0, src_path)
# Also add backend directory to path for imports
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_path)

# Import and run the bot module directly
if __name__ == "__main__":
    print("🔄 Starting bot launcher...")
    try:
        # Import the bot module and run it
        import bot
        import asyncio
        print("✅ Bot module imported successfully")
        # Run the bot's main function
        asyncio.run(bot.main())
    except Exception as e:
        print(f"❌ Failed to import or run bot module: {e}")
        import traceback
        traceback.print_exc()
