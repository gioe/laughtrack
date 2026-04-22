#!/usr/bin/env python3
"""
Lightweight Discord MCP server for Claude Code.

Exposes two tools:
  - discord_fetch_messages: Fetch recent messages from a channel/thread
  - discord_search_messages: Search messages in a channel by content

Setup:
  1. Create a Discord bot at https://discord.com/developers/applications
  2. Enable MESSAGE_CONTENT intent in the Bot settings
  3. Add bot to your server with permissions: Read Message History, Read Messages
  4. Set DISCORD_BOT_TOKEN env var (or pass via --token flag)

Usage in claude settings (mcpServers):
  "discord": {
    "command": "python3",
    "args": [".claude/mcp/discord-mcp.py"],
    "env": { "DISCORD_BOT_TOKEN": "your-bot-token" }
  }
"""

import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE_URL = "https://discord.com/api/v10"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")


def _headers():
    return {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://laughtrack.com, 0.1.0)",
    }


_SSL_CTX = ssl.create_default_context()
# macOS Python 3.11 framework build ships without the system CA bundle;
# fall back to certifi if installed, otherwise disable verification so
# the MCP server doesn't crash on SSL handshake with Discord.
try:
    import certifi
    _SSL_CTX.load_verify_locations(certifi.where())
except Exception:
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE


def _api_get(path: str, params: dict | None = None) -> dict | list:
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if qs:
            url += f"?{qs}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}", "detail": body}


def _format_message(msg: dict) -> dict:
    author = msg.get("author", {})
    return {
        "id": msg["id"],
        "author": author.get("username", "unknown"),
        "content": msg.get("content", ""),
        "timestamp": msg.get("timestamp", ""),
        "attachments": [a.get("url") for a in msg.get("attachments", [])],
        "embeds_count": len(msg.get("embeds", [])),
    }


# --- Tool implementations ---

def fetch_messages(channel_id: str, limit: int = 25, before: str | None = None, after: str | None = None) -> list[dict]:
    """Fetch recent messages from a Discord channel or thread."""
    params = {"limit": str(min(limit, 100))}
    if before:
        params["before"] = before
    if after:
        params["after"] = after
    result = _api_get(f"/channels/{channel_id}/messages", params)
    if isinstance(result, dict) and "error" in result:
        return [result]
    return [_format_message(m) for m in result]


def search_messages(channel_id: str, query: str, limit: int = 25) -> list[dict]:
    """Fetch messages and filter locally by content (Discord search API requires bot perms)."""
    # Fetch a larger batch and filter client-side for simplicity
    params = {"limit": "100"}
    result = _api_get(f"/channels/{channel_id}/messages", params)
    if isinstance(result, dict) and "error" in result:
        return [result]
    query_lower = query.lower()
    matches = [_format_message(m) for m in result if query_lower in m.get("content", "").lower()]
    return matches[:limit]


def get_channel_info(channel_id: str) -> dict:
    """Get basic info about a channel."""
    return _api_get(f"/channels/{channel_id}")


# --- MCP protocol (stdio JSON-RPC) ---

TOOLS = [
    {
        "name": "discord_fetch_messages",
        "description": "Fetch recent messages from a Discord channel or thread. Returns messages with author, content, timestamp, and attachment URLs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Discord channel or thread ID"},
                "limit": {"type": "integer", "description": "Number of messages to fetch (max 100)", "default": 25},
                "before": {"type": "string", "description": "Fetch messages before this message ID (for pagination)"},
                "after": {"type": "string", "description": "Fetch messages after this message ID"},
            },
            "required": ["channel_id"],
        },
    },
    {
        "name": "discord_search_messages",
        "description": "Search messages in a Discord channel by content (client-side filter on last 100 messages).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Discord channel or thread ID"},
                "query": {"type": "string", "description": "Text to search for (case-insensitive)"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 25},
            },
            "required": ["channel_id", "query"],
        },
    },
    {
        "name": "discord_channel_info",
        "description": "Get basic info about a Discord channel (name, topic, type).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Discord channel ID"},
            },
            "required": ["channel_id"],
        },
    },
]


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "discord-mcp", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # no response needed

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        if not TOKEN:
            text = "Error: DISCORD_BOT_TOKEN not set. Add it to the mcpServers env config."
        elif tool_name == "discord_fetch_messages":
            result = fetch_messages(
                args["channel_id"],
                limit=args.get("limit", 25),
                before=args.get("before"),
                after=args.get("after"),
            )
            text = json.dumps(result, indent=2)
        elif tool_name == "discord_search_messages":
            result = search_messages(
                args["channel_id"],
                args["query"],
                limit=args.get("limit", 25),
            )
            text = json.dumps(result, indent=2)
        elif tool_name == "discord_channel_info":
            result = get_channel_info(args["channel_id"])
            text = json.dumps(result, indent=2)
        else:
            text = f"Unknown tool: {tool_name}"

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text}],
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(req)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
