"""MCP Server for iphone-cli.

Exposes all iPhone control capabilities as MCP tools so any
MCP-compatible agent (Claude Desktop, Sandra, etc.) can control
an iPhone.

Add to your MCP config:
{
  "mcpServers": {
    "iphone": {
      "command": "iphone",
      "args": ["serve"]
    }
  }
}
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from ..core.wda import WDAClient
from ..core.screenshot import ScreenCapture


def create_server(wda_url: str = "http://localhost:8100") -> Server:
    server = Server("iphone-cli")
    wda = WDAClient(url=wda_url)
    screen = ScreenCapture(wda)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="iphone_context",
                description=(
                    "Capture the current iPhone screen. Returns a screenshot (image) "
                    "and a list of interactive UI elements with their coordinates. "
                    "This is the PRIMARY tool for understanding what's on screen. "
                    "Call this before deciding what to tap/type."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "compress": {
                            "type": "boolean",
                            "description": "Compress screenshot for faster transfer",
                            "default": True,
                        },
                    },
                },
            ),
            Tool(
                name="iphone_tap",
                description="Tap at (x, y) coordinates on the iPhone screen.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"},
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(
                name="iphone_swipe",
                description="Swipe from (x1,y1) to (x2,y2). Use for scrolling or gestures.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x1": {"type": "integer"},
                        "y1": {"type": "integer"},
                        "x2": {"type": "integer"},
                        "y2": {"type": "integer"},
                        "duration": {"type": "number", "default": 0.5},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                },
            ),
            Tool(
                name="iphone_type",
                description="Type text into the currently focused input field.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to type"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="iphone_press",
                description="Press a hardware button: home, lock, volume_up, volume_down.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "button": {
                            "type": "string",
                            "enum": ["home", "lock", "volume_up", "volume_down"],
                        },
                    },
                    "required": ["button"],
                },
            ),
            Tool(
                name="iphone_launch",
                description="Launch an app by its bundle ID (e.g., com.apple.mobilesafari).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bundle_id": {"type": "string"},
                    },
                    "required": ["bundle_id"],
                },
            ),
            Tool(
                name="iphone_kill",
                description="Terminate an app by bundle ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bundle_id": {"type": "string"},
                    },
                    "required": ["bundle_id"],
                },
            ),
            Tool(
                name="iphone_long_press",
                description="Long press at coordinates for a duration.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "duration": {"type": "number", "default": 1.0},
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(
                name="iphone_scroll",
                description="Scroll up or down on the screen.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down"],
                        },
                        "amount": {"type": "integer", "default": 300},
                    },
                    "required": ["direction"],
                },
            ),
            Tool(
                name="iphone_find",
                description="Find UI elements containing specific text. Returns elements with coordinates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to search for"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="iphone_alert",
                description="Handle a system alert/dialog: get text, accept, or dismiss.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["text", "accept", "dismiss"],
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="iphone_clipboard",
                description="Get or set the iPhone clipboard.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["get", "set"]},
                        "text": {"type": "string", "description": "Text to set (only for set)"},
                    },
                    "required": ["action"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        try:
            match name:
                case "iphone_context":
                    ctx = screen.capture(include_screenshot=True)
                    if arguments.get("compress", True):
                        ctx.screenshot_base64 = screen.compress_screenshot(
                            ctx.screenshot_base64
                        )
                    llm_ctx = ctx.for_llm(include_screenshot=False)
                    return [
                        ImageContent(
                            type="image",
                            data=ctx.screenshot_base64,
                            mimeType="image/jpeg" if arguments.get("compress", True) else "image/png",
                        ),
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "screen_size": llm_ctx["screen_size"],
                                "app": llm_ctx["app"],
                                "alert": llm_ctx.get("alert"),
                                "interactive_elements": llm_ctx["interactive_elements"][:40],
                            }, indent=2),
                        ),
                    ]

                case "iphone_tap":
                    wda.tap(arguments["x"], arguments["y"])
                    return [TextContent(type="text", text=f"Tapped at ({arguments['x']}, {arguments['y']})")]

                case "iphone_swipe":
                    wda.swipe(arguments["x1"], arguments["y1"], arguments["x2"], arguments["y2"],
                              arguments.get("duration", 0.5))
                    return [TextContent(type="text", text="Swipe completed")]

                case "iphone_type":
                    wda.type_text(arguments["text"])
                    return [TextContent(type="text", text=f"Typed: {arguments['text']}")]

                case "iphone_press":
                    btn = arguments["button"]
                    match btn:
                        case "home": wda.press_home()
                        case "lock": wda.press_lock()
                        case "volume_up": wda.volume_up()
                        case "volume_down": wda.volume_down()
                    return [TextContent(type="text", text=f"Pressed {btn}")]

                case "iphone_launch":
                    wda.launch_app(arguments["bundle_id"])
                    return [TextContent(type="text", text=f"Launched {arguments['bundle_id']}")]

                case "iphone_kill":
                    wda.kill_app(arguments["bundle_id"])
                    return [TextContent(type="text", text=f"Killed {arguments['bundle_id']}")]

                case "iphone_long_press":
                    wda.long_press(arguments["x"], arguments["y"], arguments.get("duration", 1.0))
                    return [TextContent(type="text", text=f"Long pressed at ({arguments['x']}, {arguments['y']})")]

                case "iphone_scroll":
                    if arguments["direction"] == "down":
                        wda.scroll_down(arguments.get("amount", 300))
                    else:
                        wda.scroll_up(arguments.get("amount", 300))
                    return [TextContent(type="text", text=f"Scrolled {arguments['direction']}")]

                case "iphone_find":
                    results = wda.find_by_text(arguments["text"])
                    return [TextContent(type="text", text=json.dumps(results, indent=2))]

                case "iphone_alert":
                    action = arguments["action"]
                    match action:
                        case "text":
                            return [TextContent(type="text", text=json.dumps({"alert": wda.alert_text()}))]
                        case "accept":
                            wda.alert_accept()
                            return [TextContent(type="text", text="Alert accepted")]
                        case "dismiss":
                            wda.alert_dismiss()
                            return [TextContent(type="text", text="Alert dismissed")]

                case "iphone_clipboard":
                    if arguments["action"] == "get":
                        return [TextContent(type="text", text=wda.get_clipboard())]
                    else:
                        wda.set_clipboard(arguments.get("text", ""))
                        return [TextContent(type="text", text="Clipboard set")]

                case _:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


async def _run(wda_url: str):
    server = create_server(wda_url)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


def run_server(wda_url: str = "http://localhost:8100"):
    import asyncio
    asyncio.run(_run(wda_url))
