#!/bin/bash

echo "Installing dependencies for Telegram bot..."
echo

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    echo "Activating virtual environment (Windows)..."
    source .venv/Scripts/activate
else
    echo "Virtual environment not found. Please create one first:"
    echo "python -m venv .venv"
    echo "source .venv/bin/activate  # Linux/Mac"
    echo "source .venv/Scripts/activate  # Windows"
    echo
    exit 1
fi

echo "Updating pip and build tools..."
python -m pip install --upgrade pip setuptools wheel

echo
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "Installation failed. Please check the error messages above."
    echo "On Windows, you may need to install Microsoft Visual C++ Build Tools."
    echo "Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    echo
    exit 1
fi

echo
echo "Dependencies installed successfully!"
echo "You can now run the bot with: python src/bot.py"
echo
