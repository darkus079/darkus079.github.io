#!/usr/bin/env python3
"""
Run bot with timeout for testing
"""

import asyncio
import sys
import os

# Configure paths like run_bot.py does
project_root = os.path.dirname(os.path.dirname(__file__))
tg_bot_path = os.path.dirname(__file__)
src_path = os.path.join(tg_bot_path, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, tg_bot_path)
sys.path.insert(0, src_path)
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_path)

async def run_bot_with_timeout():
    """Run bot for 10 seconds to see what happens"""
    print("🧪 Running bot for 10 seconds...")

    try:
        import src.bot as bot_module

        # Create task
        bot_task = asyncio.create_task(bot_module.main())

        # Wait for 10 seconds
        await asyncio.sleep(10)

        print("⏰ Timeout reached, cancelling bot...")
        bot_task.cancel()

        try:
            await bot_task
            print("✅ Bot cancelled successfully")
        except asyncio.CancelledError:
            print("🛑 Bot was cancelled")

    except Exception as e:
        print(f"❌ Error during bot run: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_bot_with_timeout())
