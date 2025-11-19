#!/usr/bin/env python3
"""
Final test to run the bot normally
"""

import asyncio
import signal
import sys
import os

# Configure paths
project_root = os.path.dirname(os.path.dirname(__file__))
tg_bot_path = os.path.dirname(__file__)
src_path = os.path.join(tg_bot_path, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, tg_bot_path)
sys.path.insert(0, src_path)
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_path)

async def run_with_timeout():
    """Run bot with graceful shutdown"""
    print("🚀 Starting ParskadBot...")
    print("Press Ctrl+C to stop")

    # Import bot module
    import src.bot as bot_module

    # Create shutdown event
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        print("\n🛑 Shutdown signal received...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run main function
        main_task = asyncio.create_task(bot_module.main())

        # Wait for either completion or shutdown signal
        done, pending = await asyncio.wait(
            [main_task, shutdown_event.wait()],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if main_task in done:
            # Main task completed
            try:
                result = main_task.result()
                print("✅ Bot completed normally")
            except Exception as e:
                print(f"❌ Bot failed: {e}")
                return 1
        else:
            # Shutdown signal received
            print("🛑 Bot shutdown by user")
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_with_timeout())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
