# iphone-cli

A CLI that lets you control any iPhone app over USB. Built to be the control layer for AI agents — but works standalone too.

## How It Works

```
Your code / Agent / MCP Client
  ↕ JSON commands
iphone-cli
  ↕ USB (usbmuxd)
iPhone (WebDriverAgent)
```

## Commands

| Command | What it does |
|---------|-------------|
| `iphone screenshot` | Capture screen, return base64 image |
| `iphone tap <x> <y>` | Tap at coordinates |
| `iphone long-press <x> <y>` | Long press at coordinates |
| `iphone swipe <x1> <y1> <x2> <y2>` | Swipe gesture |
| `iphone type <text>` | Type into focused field |
| `iphone key <button>` | Press home, lock, volume |
| `iphone launch <bundle_id>` | Open an app |
| `iphone kill <bundle_id>` | Close an app |
| `iphone active-app` | Get current foreground app |
| `iphone elements` | Get UI element tree (accessibility) |
| `iphone find <text>` | Find elements by text |
| `iphone context` | Screenshot + elements + app info (one call) |
| `iphone alert <accept\|dismiss\|text>` | Handle system alerts |
| `iphone clipboard <get\|set>` | Read/write clipboard |
| `iphone info` | Device info, battery, etc. |
| `iphone devices` | List connected devices |
| `iphone doctor` | Health check |
| `iphone serve` | Start MCP server |

All commands return structured JSON — pipe to `jq` or parse from any language.

## Setup

### Prerequisites

1. **Python 3.10+**
2. **iPhone with Developer Mode enabled** (Settings → Privacy → Developer Mode)
3. **Apple Developer account** (free works) to sign WebDriverAgent
4. **USB cable** connecting iPhone to host machine

### Install

```bash
pip install iphone-cli
```

Or from source:

```bash
git clone https://github.com/your-org/iphone-cli
cd iphone-cli
pip install -e .
```

### First-Time Setup

```bash
# 1. Trust the computer on your iPhone when prompted
iphone pair

# 2. Install WebDriverAgent on the device (requires Xcode on macOS)
python scripts/setup_wda.py --team-id YOUR_TEAM_ID

# 3. Verify everything works
iphone doctor
```

## Usage

### CLI

```bash
# See what's on screen
iphone screenshot --save screen.png

# Tap a button
iphone tap 200 450

# Type into a search bar
iphone type "weather in dallas"

# Launch Safari
iphone launch com.apple.mobilesafari

# Get everything an agent needs in one call
iphone context
```

### Python SDK

```python
from iphone_cli.sdk import iPhone

phone = iPhone()

phone.screenshot(path="screen.png")
phone.tap(200, 450)
phone.type_text("hello world")
phone.swipe(200, 600, 200, 200, duration=0.5)
phone.launch("com.apple.mobilesafari")

# Full context for agent consumption
ctx = phone.context()
print(ctx.elements_summary)  # interactive elements with coordinates
print(ctx.active_app)        # what app is open
```

### MCP Server

```bash
iphone serve
```

Exposes all commands as MCP tools. Add to your agent config:

```json
{
  "mcpServers": {
    "iphone": {
      "command": "iphone",
      "args": ["serve"]
    }
  }
}
```

Then any MCP client can call `iphone_tap`, `iphone_screenshot`, `iphone_context`, etc.

## The `context` Command

The most important command for agent integration. Returns everything in one call:

```bash
iphone context
```

```json
{
  "screenshot": "<base64 image>",
  "screen_size": "390x844",
  "app": "com.apple.mobilesafari",
  "interactive_elements": [
    {
      "type": "Button",
      "label": "Search",
      "center": [195, 52],
      "rect": {"x": 50, "y": 32, "width": 290, "height": 40}
    },
    {
      "type": "Link",
      "label": "Apple",
      "center": [195, 300],
      "rect": {"x": 20, "y": 280, "width": 350, "height": 40}
    }
  ]
}
```

An agent sees the screenshot (vision) AND the element tree (structured data with tap coordinates). That's everything needed to decide what to do next.

## Architecture

```
iphone_cli/
├── __init__.py
├── cli.py              # Click CLI entry point
├── sdk.py              # High-level Python interface
├── core/
│   ├── __init__.py     # Device discovery, pairing, info
│   ├── wda.py          # WebDriverAgent client (UI automation)
│   └── screenshot.py   # Screen capture + context generation
├── mcp/
│   └── __init__.py     # MCP server wrapper
```

## Key Dependencies

- **pymobiledevice3** — speaks all iOS protocols over USB
- **WebDriverAgent** — UI automation server running on-device
- **click** — CLI framework
- **Pillow** — screenshot processing
- **rich** — pretty terminal output

## License

MIT
