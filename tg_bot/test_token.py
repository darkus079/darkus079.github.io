#!/usr/bin/env python3
"""
Test script to validate Telegram bot token
"""

import asyncio
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

async def test_token():
    """Test bot token validity"""
    print("🔍 Testing Telegram bot token...")

    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from src.config import settings

        print(f"🤖 Token to test: {settings.TELEGRAM_BOT_TOKEN[:15]}...")

        # Create bot instance
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )

        print("🔗 Attempting to get bot info...")
        # Try to get bot info
        bot_info = await bot.get_me()

        print("✅ Token is valid!")
        print(f"🤖 Bot username: @{bot_info.username}")
        print(f"📝 Bot name: {bot_info.first_name}")
        print(f"🆔 Bot ID: {bot_info.id}")
        print(f"📱 Can join groups: {bot_info.can_join_groups}")
        print(f"📨 Can read messages: {bot_info.can_read_all_group_messages}")

        await bot.close()

    except Exception as e:
        print(f"❌ Token validation failed: {e}")
        print("\n🔧 Possible issues:")
        print("1. Invalid token format")
        print("2. Token revoked by @BotFather")
        print("3. Network connectivity issues")
        print("4. Telegram API restrictions")

        # Check token format
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or len(token) < 45:
            print("⚠️ Token appears to be too short")
        elif not token.replace(':', '').replace('_', '').isalnum():
            print("⚠️ Token contains invalid characters")
        else:
            print("✅ Token format looks correct")

        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_token())
