# Download Manager

A comprehensive multi-threaded download manager application inspired by Internet Download Manager (IDM), featuring accelerated downloads, browser integration, video detection, and advanced scheduling capabilities.

## Features

### Core Functionality
- **Multi-threaded Downloads**: Accelerates downloads by splitting files into parts and downloading them concurrently (up to 8 threads)
- **Pause/Resume Support**: Seamlessly pause and resume downloads using HTTP Range requests
- **Download Acceleration**: Increases download speeds by bypassing server connection limits
- **Error Handling**: Automatic retry mechanism with configurable retry attempts
- **File Integrity Verification**: Ensures downloaded files are complete and uncorrupted

### Browser Integration
- **URL Capture**: Automatically captures download links from web browsers
- **Protocol Handler**: Registers custom protocol for seamless browser integration
- **Extension Support**: Native messaging host for browser extensions (Chrome/Firefox)
- **Link Detection**: Automatically detects downloadable file types

### Video Detection & Downloading
- **Platform Support**: YouTube, Vimeo, Dailymotion, Twitch, and more
- **Quality Selection**: Automatically selects best available quality
- **Direct URL Extraction**: Extracts direct download URLs from video platforms
- **Multiple Formats**: Supports various video formats (MP4, AVI, MKV, etc.)

### Advanced Features
- **Download Scheduling**: Schedule downloads for specific times or recurring intervals
- **File Organization**: Automatically categorizes files into folders by type
- **System Notifications**: Desktop notifications for download events
- **Bandwidth Control**: Limit download speeds to manage network usage
- **Persistent Storage**: SQLite database for download history and resume data

### User Interface
- **Modern GUI**: Clean, intuitive interface built with PyQt5
- **Progress Tracking**: Real-time progress bars with speed and ETA information
- **System Tray**: Minimize to system tray for background operation
- **Keyboard Shortcuts**: Quick access to common functions
- **Dark/Light Themes**: Customizable appearance

## Architecture

The application follows a modular architecture with the following components:

```
Download Manager
├── Core Components
│   ├── Download Manager (Orchestration)
│   ├── Download Engine (Multi-threading)
│   ├── Download Task (State Management)
│   └── Scheduler (Time-based triggers)
├── Network Layer
│   └── HTTP Client (Requests & Range support)
├── File System
│   └── File Manager (Storage & merging)
├── Database
│   └── SQLite Manager (Persistence)
├── Browser Integration
│   └── URL Capture (Protocol handling)
├── Video Detection
│   └── Platform-specific extractors
├── User Interface
│   ├── Main Window (Primary interface)
│   └── Download Items (Individual widgets)
├── Notifications
│   └── System notifications
└── Configuration
    └── Settings management
```

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Dependencies
Install required dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- `PyQt5` - GUI framework
- `requests` - HTTP client
- `aiohttp` - Async HTTP client
- `sqlite3` - Database (built-in)
- `plyer` - Cross-platform notifications
- `youtube-dl` - Video extraction (optional)
- `pytube` - YouTube downloader (optional)
- `validators` - URL validation
- `psutil` - System utilities
- `cryptography` - Security features

### Optional Dependencies
For enhanced video support:
```bash
pip install youtube-dl pytube
```

For Windows toast notifications:
```bash
pip install win10toast
```

## Usage

### Basic Usage
Start the application:
```bash
python main.py
```

Add a download directly:
```bash
python main.py "https://example.com/file.zip"
```

### Browser Integration
Register protocol handler:
```bash
python main.py --register-protocol
```

Unregister protocol handler:
```bash
python main.py --unregister-protocol
```

### Configuration
The application stores configuration in:
- **Windows**: `%APPDATA%/DownloadManager/`
- **macOS**: `~/Library/Application Support/DownloadManager/`
- **Linux**: `~/.downloadmanager/`

### Settings
Key configuration options:
- `download_directory`: Default download location
- `max_concurrent_downloads`: Maximum simultaneous downloads (default: 3)
- `max_threads_per_download`: Threads per download (default: 8)
- `enable_notifications`: Desktop notifications (default: true)
- `enable_browser_integration`: Browser URL capture (default: true)
- `auto_organize_files`: Organize files by category (default: true)

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Add Downloads**:
   - Enter a URL in the input field and click "Add Download"
   - Or drag and drop URLs into the application
   - Or use browser integration for automatic capture

4. **Manage Downloads**:
   - Use the control buttons to start, pause, resume, or cancel downloads
   - Double-click completed downloads to open the file location
   - Right-click for additional options

## Platform Support

### Windows
- Full feature support including system tray and toast notifications
- Protocol handler registration for browser integration
- Native file operations and system integration

### macOS
- Core functionality with system notifications
- Limited protocol handler support
- Native file operations

### Linux
- Core functionality with notify-send notifications
- Protocol handler via .desktop files
- Standard file operations

## License

This project is licensed under the MIT License.