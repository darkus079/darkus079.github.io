#!/usr/bin/env python3
"""
Test script to run bot for a short time and show logs
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

async def test_run():
    """Run bot for 3 seconds to see initialization logs"""
    print("🧪 Starting bot test run (3 seconds)...")

    try:
        # Import and run main function but with timeout
        import src.bot as bot_module

        # Create a task for the main function
        main_task = asyncio.create_task(bot_module.main())

        # Wait for 3 seconds or until completion
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
            print("✅ Bot completed within 3 seconds")
        except asyncio.TimeoutError:
            print("⏰ Bot is still running after 3 seconds (this is normal)")
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                print("🛑 Bot cancelled successfully")

    except Exception as e:
        print(f"❌ Bot test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_run())
