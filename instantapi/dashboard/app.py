"""Web dashboard for managing InstantAPI scraped APIs."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import html as html_module

from instantapi.storage.db import delete_api, get_api, list_apis

dashboard_app = FastAPI(
    title="InstantAPI Dashboard",
    description="Manage your scraped APIs",
)

dashboard_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard_home() -> str:
    """Render the main dashboard page."""
    apis = await list_apis()
    rows = ""
    for api in apis:
        safe_url = html_module.escape(api['url'][:60])
        safe_url_attr = html_module.escape(api['url'])
        safe_desc = html_module.escape(api.get('site_description', '')[:50])
        safe_date = html_module.escape(api['created_at'][:19].replace('T', ' '))
        api_id = int(api['id'])
        rows += f"""
        <tr>
            <td class="px-4 py-2 text-sm font-mono text-cyan-400">{api_id}</td>
            <td class="px-4 py-2 text-sm truncate max-w-xs" title="{safe_url_attr}">{safe_url}</td>
            <td class="px-4 py-2 text-sm text-gray-300">{safe_desc}</td>
            <td class="px-4 py-2 text-sm text-gray-400">{safe_date}</td>
            <td class="px-4 py-2 text-sm space-x-2">
                <a href="/api/{api_id}" target="_blank"
                   class="text-cyan-400 hover:text-cyan-300 underline">Detail</a>
                <form method="POST" action="/delete/{api_id}" style="display:inline"
                      onsubmit="return confirm('Delete API #{api_id}?')">
                    <button type="submit" class="text-red-400 hover:text-red-300 underline bg-transparent border-0 cursor-pointer p-0">Delete</button>
                </form>
            </td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InstantAPI Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background: #0d1117; color: #e6edf3; font-family: 'Segoe UI', sans-serif; }}
        .glow {{ box-shadow: 0 0 20px rgba(0, 255, 255, 0.15); }}
    </style>
</head>
<body class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto">

        <!-- Header -->
        <div class="flex items-center gap-4 mb-8">
            <div class="text-3xl">⚡</div>
            <div>
                <h1 class="text-2xl font-bold text-white">InstantAPI</h1>
                <p class="text-gray-400 text-sm">Dashboard — manage your scraped APIs</p>
            </div>
            <div class="ml-auto text-sm text-gray-500">
                {len(apis)} API{'s' if len(apis) != 1 else ''} saved
            </div>
        </div>

        <!-- Quick Start -->
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6 glow">
            <p class="text-sm text-gray-400 mb-2">Quick Start</p>
            <code class="text-cyan-400 text-sm">instantapi scrape https://example.com</code>
        </div>

        <!-- APIs Table -->
        <div class="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <div class="px-4 py-3 border-b border-gray-800">
                <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Saved APIs</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-800">
                        <tr>
                            <th class="px-4 py-2 text-left text-xs text-gray-400 uppercase">ID</th>
                            <th class="px-4 py-2 text-left text-xs text-gray-400 uppercase">URL</th>
                            <th class="px-4 py-2 text-left text-xs text-gray-400 uppercase">Description</th>
                            <th class="px-4 py-2 text-left text-xs text-gray-400 uppercase">Created</th>
                            <th class="px-4 py-2 text-left text-xs text-gray-400 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800">
                        {rows if rows else '<tr><td colspan="5" class="px-4 py-8 text-center text-gray-500">No APIs yet. Run <code class=\'text-cyan-400\'>instantapi scrape &lt;url&gt;</code> to get started.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center text-gray-600 text-xs">
            <a href="https://github.com/gacorpoll-ui/Instant_API" class="hover:text-gray-400">InstantAPI on GitHub</a>
        </div>
    </div>
</body>
</html>"""


@dashboard_app.get("/api/{api_id}", response_class=HTMLResponse)
async def dashboard_api_detail(api_id: int) -> str:
    """Show details for a specific API."""
    result = await get_api(api_id)
    if not result:
        return "<h1>Not Found</h1><p>API not found.</p>"

        safe_url = html_module.escape(result.source_url)
        safe_desc = html_module.escape(result.site_description or result.source_url)
        endpoints_html = ""
    for ep in result.endpoints:
        safe_ep_method = html_module.escape(ep.method)
        safe_ep_name = html_module.escape(ep.name)
        safe_ep_desc = html_module.escape(ep.description[:80])
        fields_html = "".join(
            f'<tr><td class="py-1 pr-4 text-cyan-400 font-mono text-xs">{html_module.escape(name)}</td>'
            f'<td class="py-1 pr-4 text-yellow-400 text-xs">{html_module.escape(field.type)}</td>'
            f'<td class="py-1 text-gray-400 text-xs">{html_module.escape(field.description)}</td></tr>'
            for name, field in ep.schema_fields.items()
        )
        sample_preview = ""
        if ep.sample_data:
            import json
            sample_preview = f"""<details class="mt-2">
                <summary class="text-xs text-gray-400 cursor-pointer">Sample Data ({len(ep.sample_data)} items)</summary>
                <pre class="text-xs text-gray-300 bg-black rounded p-3 mt-2 overflow-x-auto">{json.dumps(ep.sample_data[:2], indent=2)}</pre>
            </details>"""

        endpoints_html += f"""
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-4">
            <div class="flex items-center gap-3 mb-3">
                <span class="bg-green-900 text-green-400 text-xs font-bold px-2 py-0.5 rounded">{safe_ep_method}</span>
                <code class="text-cyan-400 font-mono">/api/{safe_ep_name}</code>
                <span class="text-gray-400 text-sm ml-2">{safe_ep_desc}</span>
                <span class="ml-auto text-xs text-gray-500">{ep.item_count} items</span>
            </div>
            <table class="w-full">
                <thead><tr>
                    <th class="text-left text-xs text-gray-500 pb-1">Field</th>
                    <th class="text-left text-xs text-gray-500 pb-1">Type</th>
                    <th class="text-left text-xs text-gray-500 pb-1">Description</th>
                </tr></thead>
                <tbody>{fields_html}</tbody>
            </table>
            {sample_preview}
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>API #{api_id} — InstantAPI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body {{ background: #0d1117; color: #e6edf3; }}</style>
</head>
<body class="min-h-screen p-8">
    <div class="max-w-4xl mx-auto">
        <div class="flex items-center gap-3 mb-6">
            <a href="/" class="text-gray-400 hover:text-white text-sm">← Dashboard</a>
            <span class="text-gray-600">/</span>
            <span class="text-white font-semibold">API #{api_id}</span>
        </div>
        <div class="mb-6">
            <h1 class="text-xl font-bold text-white mb-1">{safe_desc}</h1>
            <p class="text-gray-400 text-sm">{safe_url}</p>
        </div>
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Endpoints</h2>
        {endpoints_html}
    </div>
</body>
</html>"""


@dashboard_app.post("/delete/{api_id}")
async def dashboard_delete_api(api_id: int):
    """Delete an API and redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    await delete_api(api_id)
    return RedirectResponse(url="/", status_code=302)


def run_dashboard(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the dashboard server."""
    import uvicorn
    uvicorn.run(dashboard_app, host=host, port=port, log_level="warning")
