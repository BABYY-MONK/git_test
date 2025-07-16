#!/usr/bin/env python3
"""
Simple launcher script for the Download Manager application.
This script handles dependency checking and provides helpful error messages.
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        ("PyQt5", "PyQt5"),
        ("requests", "requests"),
        ("aiohttp", "aiohttp"),
        ("validators", "validators"),
        ("plyer", "plyer"),
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("Missing required dependencies:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nTo install missing dependencies, run:")
        print("  pip install -r requirements.txt")
        print("\nOr install individually:")
        for package in missing_packages:
            print(f"  pip install {package}")
        return False
    
    return True

def install_dependencies():
    """Attempt to install dependencies automatically."""
    print("Attempting to install dependencies...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("Error: requirements.txt not found")
        return False
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def main():
    """Main launcher function."""
    print("Download Manager Launcher")
    print("=" * 30)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check dependencies
    if not check_dependencies():
        response = input("\nWould you like to install missing dependencies? (y/n): ")
        if response.lower() in ['y', 'yes']:
            if not install_dependencies():
                return 1
            print("\nDependencies installed. Please run the script again.")
            return 0
        else:
            print("Cannot run without required dependencies.")
            return 1
    
    # Import and run the main application
    try:
        print("Starting Download Manager...")
        from main import main as app_main
        return app_main()
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
