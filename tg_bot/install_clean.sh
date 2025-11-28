#!/bin/bash

echo "Installing dependencies for Telegram bot (clean installation)..."
echo

# Check if venv_clean exists, create if not
if [ ! -d "venv_clean" ]; then
    echo "Creating clean virtual environment..."
    python -m venv venv_clean
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please check Python installation."
        exit 1
    fi
fi

# Activate virtual environment
if [ -f "venv_clean/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv_clean/bin/activate
elif [ -f "venv_clean/Scripts/activate" ]; then
    echo "Activating virtual environment (Windows)..."
    source venv_clean/Scripts/activate
else
    echo "Virtual environment not found. Please create one first:"
    echo "python -m venv venv_clean"
    echo "source venv_clean/bin/activate  # Linux/Mac"
    echo "source venv_clean/Scripts/activate  # Windows"
    echo
    exit 1
fi

echo "Clearing pip cache..."
python -m pip cache purge

echo "Updating pip and build tools..."
python -m pip install --upgrade pip setuptools wheel

echo
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "Installation failed. Please check the error messages above."
    echo "Common solutions:"
    echo "1. Clear pip cache: python -m pip cache purge"
    echo "2. Use Python 3.11 or 3.12 instead of 3.13"
    echo "3. Create new virtual environment: python -m venv venv_clean"
    echo "4. See BUG.md for detailed troubleshooting"
    echo
    exit 1
fi

echo
echo "Dependencies installed successfully!"
echo "You can now run the bot with:"
echo "source venv_clean/bin/activate  # Linux/Mac"
echo "venv_clean\Scripts\activate      # Windows"
echo "python src/bot.py"
echo
