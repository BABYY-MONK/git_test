#!/usr/bin/env python3
"""
Setup script for the Download Manager application.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split("\n")
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith("#")]

setup(
    name="download-manager",
    version="1.0.0",
    description="A comprehensive multi-threaded download manager with browser integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Download Manager Team",
    author_email="contact@downloadmanager.com",
    url="https://github.com/downloadmanager/download-manager",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "video": ["youtube-dl", "pytube"],
        "notifications": ["plyer", "win10toast"],
        "dev": ["pytest", "pytest-cov", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "download-manager=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    keywords="download manager, multi-threaded, browser integration, video downloader",
    project_urls={
        "Bug Reports": "https://github.com/downloadmanager/download-manager/issues",
        "Source": "https://github.com/downloadmanager/download-manager",
        "Documentation": "https://github.com/downloadmanager/download-manager/wiki",
    },
)
