#!/usr/bin/env python3
"""
Test script to check bot configuration loading
"""

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

print("🔧 Testing configuration loading...")
print(f"Project root: {project_root}")
print(f"Backend path: {backend_path}")

try:
    from src.config import settings
    print("✅ Config loaded successfully")
    print(f"🤖 Token: {settings.TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"👥 Admins: {settings.ADMIN_IDS}")
    print(f"📊 Log level: {settings.LOG_LEVEL}")
    print(f"⚙️ Default mode: {settings.DEFAULT_MODE}")
    print(f"📈 Global limit: {settings.GLOBAL_DAILY_LIMIT}")
except Exception as e:
    print(f"❌ Config loading failed: {e}")
    import traceback
    traceback.print_exc()

print("\n🔍 Testing backend import...")
try:
    from backend.parser_simplified import KadArbitrParser
    print("✅ Backend parser imported successfully")
except Exception as e:
    print(f"❌ Backend import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n🎯 Configuration test completed!")
