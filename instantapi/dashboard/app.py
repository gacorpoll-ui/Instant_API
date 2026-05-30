"""Web dashboard for managing InstantAPI scraped APIs."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from instantapi.storage.db import delete_api, get_api, list_apis
from instantapi.api.generator import process_items

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
        rows += f"""
        <tr class="hover:bg-gray-800/40 transition-colors">
            <td class="px-4 py-3 text-sm font-mono text-cyan-400 font-semibold">{api['id']}</td>
            <td class="px-4 py-3 text-sm font-medium text-white truncate max-w-xs" title="{api['url']}">{api['url'][:60]}</td>
            <td class="px-4 py-3 text-sm text-gray-300">{api.get('site_description', '')[:50] or 'No description'}</td>
            <td class="px-4 py-3 text-sm text-gray-400 font-mono">{api['created_at'][:19].replace('T',' ')}</td>
            <td class="px-4 py-3 text-sm space-x-3">
                <a href="/api/{api['id']}" 
                   class="text-cyan-400 hover:text-cyan-300 font-semibold hover:underline">Playground & Details →</a>
                <a href="/delete/{api['id']}"
                   class="text-red-400 hover:text-red-300 font-medium hover:underline"
                   onclick="return confirm('Delete API #{api['id']}?')">Delete</a>
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
        body {{ background: #0b0f17; color: #e6edf3; font-family: 'Inter', system-ui, sans-serif; }}
        .glow {{ box-shadow: 0 0 25px rgba(6, 182, 212, 0.08); }}
    </style>
</head>
<body class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto">

        <!-- Header -->
        <div class="flex items-center gap-4 mb-8">
            <div class="text-4xl animate-bounce">⚡</div>
            <div>
                <h1 class="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">InstantAPI</h1>
                <p class="text-gray-400 text-sm mt-0.5">Unified API Gateway & Scraper Dashboard</p>
            </div>
            <div class="ml-auto text-xs font-semibold px-3 py-1 bg-cyan-950/40 border border-cyan-800/40 text-cyan-400 rounded-full">
                {len(apis)} API{'s' if len(apis) != 1 else ''} active
            </div>
        </div>

        <!-- Quick Start -->
        <div class="bg-gray-900/50 border border-gray-800/80 rounded-xl p-5 mb-8 glow flex items-center justify-between">
            <div>
                <h3 class="text-sm font-semibold text-white mb-1">Scrape a website and start serving instantly</h3>
                <p class="text-xs text-gray-400">Run this command in your terminal to generate new endpoints:</p>
            </div>
            <code class="text-cyan-400 font-mono text-sm bg-black/40 px-4 py-2 rounded-lg border border-gray-800">instantapi scrape <span class="text-gray-500">&lt;url&gt;</span></code>
        </div>

        <!-- APIs Table -->
        <div class="bg-gray-900/30 border border-gray-800/80 rounded-xl overflow-hidden backdrop-blur-md glow">
            <div class="px-5 py-4 border-b border-gray-800/80 bg-gray-900/20 flex justify-between items-center">
                <h2 class="text-sm font-bold text-gray-300 uppercase tracking-wider">Active Scraped APIs</h2>
                <span class="text-xs text-gray-500 font-mono">Gateway Prefix: <code class="text-cyan-500">/api/v1/{{id}}/</code></span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-gray-900/40 border-b border-gray-800/80">
                        <tr>
                            <th class="px-4 py-3 text-xs font-bold text-gray-400 uppercase tracking-wider">ID</th>
                            <th class="px-4 py-3 text-xs font-bold text-gray-400 uppercase tracking-wider">Source URL</th>
                            <th class="px-4 py-3 text-xs font-bold text-gray-400 uppercase tracking-wider">AI Description</th>
                            <th class="px-4 py-3 text-xs font-bold text-gray-400 uppercase tracking-wider">Created At</th>
                            <th class="px-4 py-3 text-xs font-bold text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800/60">
                        {rows if rows else '<tr><td colspan="5" class="px-4 py-12 text-center text-gray-500">No APIs found. Run <code class=\'text-cyan-400\'>instantapi scrape &lt;url&gt;</code> to create your first API gateway!</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div class="mt-12 text-center text-gray-600 text-xs">
            <a href="https://github.com/riri/instantapi" class="hover:text-gray-400 transition-colors">InstantAPI on GitHub</a>
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

    options_html = "".join(
        f'<option value="{ep.name}">GET /api/{ep.name}</option>'
        for ep in result.endpoints
    )

    endpoints_html = ""
    for ep in result.endpoints:
        fields_html = "".join(
            f'<tr class="border-b border-gray-800/40"><td class="py-1.5 pr-4 text-cyan-400 font-mono text-xs font-semibold">{name}</td>'
            f'<td class="py-1.5 pr-4 text-yellow-500 font-mono text-xs font-semibold">{field.type}</td>'
            f'<td class="py-1.5 text-gray-400 text-xs">{field.description or "No description"}</td></tr>'
            for name, field in ep.schema_fields.items()
        )
        sample_preview = ""
        if ep.sample_data:
            import json
            sample_preview = f"""<details class="mt-3 group">
                <summary class="text-xs text-gray-400 hover:text-white cursor-pointer select-none font-medium flex items-center gap-1.5">
                    <span class="inline-block transition-transform group-open:rotate-90">▸</span> Sample Payload Preview ({len(ep.sample_data)} items)
                </summary>
                <pre class="text-xs text-gray-300 bg-black/60 border border-gray-800 rounded-lg p-3.5 mt-2 overflow-x-auto font-mono">{json.dumps(ep.sample_data[:2], indent=2)}</pre>
            </details>"""

        endpoints_html += f"""
        <div class="bg-gray-900/40 border border-gray-800/80 rounded-xl p-5 mb-5 glow">
            <div class="flex items-center gap-3 mb-4">
                <span class="bg-green-950 border border-green-800/60 text-green-400 text-xs font-bold px-2 py-0.5 rounded font-mono">GET</span>
                <code class="text-cyan-400 font-mono text-sm font-semibold">/api/v1/{api_id}/{ep.name}</code>
                <span class="ml-auto text-xs text-gray-500 font-semibold">{ep.item_count} items detected</span>
            </div>
            <p class="text-xs text-gray-400 mb-4">{ep.description or "No endpoint description"}</p>
            <table class="w-full text-left">
                <thead><tr class="border-b border-gray-800">
                    <th class="text-left text-xs font-bold text-gray-500 pb-1.5 uppercase">Field</th>
                    <th class="text-left text-xs font-bold text-gray-500 pb-1.5 uppercase">Type</th>
                    <th class="text-left text-xs font-bold text-gray-500 pb-1.5 uppercase">Description</th>
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
    <title>API #{api_id} Playground & Details — InstantAPI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background: #0b0f17; color: #e6edf3; font-family: 'Inter', system-ui, sans-serif; }}
        .glow {{ box-shadow: 0 0 25px rgba(6, 182, 212, 0.05); }}
    </style>
</head>
<body class="min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        
        <!-- Breadcrumb & Top Bar -->
        <div class="flex items-center gap-3 mb-6">
            <a href="/" class="text-gray-400 hover:text-white text-sm transition-colors">← Back to Dashboard</a>
            <span class="text-gray-700">/</span>
            <span class="text-white text-sm font-semibold">API Gateway #{api_id}</span>
        </div>

        <!-- API Header Info -->
        <div class="bg-gray-900/30 border border-gray-800/80 rounded-xl p-5 mb-8 flex justify-between items-center backdrop-blur-md">
            <div>
                <h1 class="text-2xl font-extrabold text-white mb-1">{result.site_description or 'API Gateway'}</h1>
                <p class="text-gray-400 text-xs font-mono">Source URL: <a href="{result.source_url}" target="_blank" class="text-cyan-400 hover:underline">{result.source_url}</a></p>
            </div>
            <div class="text-right">
                <span class="text-xs text-gray-500 font-mono block">Gateway URL Prefix</span>
                <code class="text-cyan-400 font-mono text-sm bg-black/40 px-3 py-1.5 rounded-lg border border-gray-800 block mt-1">/api/v1/{api_id}/[endpoint]</code>
            </div>
        </div>

        <!-- Grid Layout -->
        <div class="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
            
            <!-- Endpoints Section (Left Column) -->
            <div class="md:col-span-7">
                <h2 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Endpoints & Schema</h2>
                {endpoints_html}
            </div>
            
            <!-- Live Playground Section (Right Column) -->
            <div class="md:col-span-5 sticky top-8">
                <div class="bg-gray-900/60 border border-cyan-800/40 rounded-xl p-6 glow backdrop-blur-md">
                    <div class="flex items-center gap-2 mb-4">
                        <span class="text-xl">🎨</span>
                        <div>
                            <h2 class="text-base font-extrabold text-white">Interactive Playground</h2>
                            <p class="text-xs text-gray-400">Test dynamic gateway endpoints live</p>
                        </div>
                    </div>

                    <!-- Config Form -->
                    <div class="space-y-4 mb-6">
                        <div>
                            <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5">Endpoint</label>
                            <select id="endpoint-select" class="w-full bg-black/50 border border-gray-800 rounded-lg px-3 py-2 text-sm text-cyan-400 font-semibold focus:outline-none focus:border-cyan-500">
                                {options_html}
                            </select>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5">Search Query (q)</label>
                                <input type="text" id="param-q" placeholder="e.g. news" class="w-full bg-black/50 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500">
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5">Sort Field</label>
                                <input type="text" id="param-sort" placeholder="e.g. score" class="w-full bg-black/50 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500">
                            </div>
                        </div>

                        <div class="grid grid-cols-3 gap-4">
                            <div>
                                <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5">Order</label>
                                <select id="param-order" class="w-full bg-black/50 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500">
                                    <option value="asc">Ascending</option>
                                    <option value="desc">Descending</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5">Limit</label>
                                <input type="number" id="param-limit" value="5" min="1" max="100" class="w-full bg-black/50 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono">
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5">Page</label>
                                <input type="number" id="param-page" value="1" min="1" class="w-full bg-black/50 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono">
                            </div>
                        </div>

                        <button onclick="sendRequest()" class="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold py-2.5 px-4 rounded-lg shadow-lg shadow-cyan-500/10 hover:shadow-cyan-500/20 active:scale-[0.98] transition-all text-sm uppercase tracking-wider">
                            Send Live Request 🚀
                        </button>
                    </div>

                    <!-- Live URL Display -->
                    <div class="mb-4">
                        <span class="block text-xs font-bold text-gray-500 uppercase mb-1">Live Request URL</span>
                        <div class="bg-black/40 border border-gray-850 p-2.5 rounded-lg overflow-x-auto text-[11px] font-mono text-cyan-400 max-w-full">
                            <a id="req-url" href="#" target="_blank" class="hover:underline select-all">Send a request to see the live URL!</a>
                        </div>
                    </div>

                    <!-- Response Viewer -->
                    <div>
                        <div class="flex justify-between items-center mb-1.5">
                            <span class="text-xs font-bold text-gray-500 uppercase">Response payload</span>
                            <div class="flex items-center gap-3">
                                <span id="resp-time" class="text-[10px] font-mono text-gray-500">0ms</span>
                                <span id="resp-status" class="px-2 py-0.5 text-[10px] font-bold bg-gray-800 text-gray-400 rounded">READY</span>
                            </div>
                        </div>
                        <pre id="response-box" class="w-full h-80 bg-black/80 border border-gray-850 rounded-lg p-3 text-xs text-green-400 overflow-y-auto font-mono scrollbar-thin select-all">Click "Send Live Request" to perform a real-time gateway fetch query!</pre>
                    </div>
                </div>
            </div>

        </div>

    </div>

    <!-- Playground Controller Script -->
    <script>
        async function sendRequest() {{
            const apiId = {api_id};
            const endpoint = document.getElementById('endpoint-select').value;
            const q = document.getElementById('param-q').value;
            const sort = document.getElementById('param-sort').value;
            const order = document.getElementById('param-order').value;
            const limit = document.getElementById('param-limit').value;
            const page = document.getElementById('param-page').value;

            let url = `/api/v1/${{apiId}}/${{endpoint}}?page=${{page}}&limit=${{limit}}&order=${{order}}`;
            if (q) url += `&q=${{encodeURIComponent(q)}}`;
            if (sort) url += `&sort=${{encodeURIComponent(sort)}}`;

            // Display Live URL
            const urlDisplay = document.getElementById('req-url');
            urlDisplay.href = url;
            urlDisplay.textContent = window.location.origin + url;

            // Show Loading
            const responseBox = document.getElementById('response-box');
            responseBox.style.color = '#38bdf8'; // Sky blue
            responseBox.textContent = 'Gateway routing connection initiated. Fetching payload...';
            
            const startTime = performance.now();
            try {{
                const res = await fetch(url);
                const duration = (performance.now() - startTime).toFixed(0);
                document.getElementById('resp-time').textContent = duration + 'ms';
                
                const statusEl = document.getElementById('resp-status');
                statusEl.textContent = res.status + ' ' + res.statusText;
                if (res.ok) {{
                    statusEl.className = 'px-2 py-0.5 text-[10px] font-bold bg-green-950 text-green-400 border border-green-800/40 rounded';
                    responseBox.style.color = '#4ade80'; // Emerald green
                }} else {{
                    statusEl.className = 'px-2 py-0.5 text-[10px] font-bold bg-red-950 text-red-400 border border-red-800/40 rounded';
                    responseBox.style.color = '#f87171'; // Coral red
                }}

                const data = await res.json();
                responseBox.textContent = JSON.stringify(data, null, 2);
            }} catch (err) {{
                document.getElementById('resp-status').textContent = 'CONNECTION ERROR';
                document.getElementById('resp-status').className = 'px-2 py-0.5 text-[10px] font-bold bg-red-950 text-red-400 border border-red-800/40 rounded';
                responseBox.style.color = '#ef4444';
                responseBox.textContent = err.message;
            }}
        }}
    </script>
</body>
</html>"""


# ─── Dynamic API Gateway Endpoints ───────────────────────────────────────────


@dashboard_app.get("/api/v1/{api_id}/{endpoint_name}", tags=["gateway"])
async def gateway_list_items(
    api_id: int,
    endpoint_name: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    q: str = Query("", description="Full-text search across all fields"),
    sort: str = Query("", description="Sort by field"),
    order: str = Query("asc", description="Sort order: asc or desc"),
) -> dict[str, Any]:
    """Dynamic gateway endpoint listing with pagination, search, and sorting."""
    result = await get_api(api_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"API #{api_id} not found")

    endpoint = next((ep for ep in result.endpoints if ep.name == endpoint_name), None)
    if not endpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint '{endpoint_name}' not found on API #{api_id}",
        )

    fields = list(endpoint.schema_fields.keys())
    res = process_items(endpoint.sample_data, q, sort, order, page, limit, fields)
    res["meta"] = {
        "endpoint": f"/api/v1/{api_id}/{endpoint_name}",
        "fields": fields,
    }
    return res


@dashboard_app.get("/api/v1/{api_id}/{endpoint_name}/search", tags=["gateway"])
async def gateway_search_items(
    api_id: int,
    endpoint_name: str,
    q: str = Query(..., description="Search query"),
    field: str = Query("", description="Limit search to a specific field"),
) -> dict[str, Any]:
    """Dynamic gateway advanced search endpoint."""
    result = await get_api(api_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"API #{api_id} not found")

    endpoint = next((ep for ep in result.endpoints if ep.name == endpoint_name), None)
    if not endpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint '{endpoint_name}' not found on API #{api_id}",
        )

    data = endpoint.sample_data
    q_lower = q.lower()

    if field:
        results = [
            item
            for item in data
            if field in item and q_lower in str(item[field]).lower()
        ]
    else:
        results = [
            item
            for item in data
            if any(q_lower in str(v).lower() for v in item.values())
        ]

    return {
        "data": results,
        "query": q,
        "field": field or "all",
        "count": len(results),
    }


@dashboard_app.get("/api/v1/{api_id}/{endpoint_name}/schema", tags=["gateway"])
async def gateway_get_schema(
    api_id: int,
    endpoint_name: str,
) -> dict[str, Any]:
    """Dynamic gateway schema info endpoint."""
    result = await get_api(api_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"API #{api_id} not found")

    endpoint = next((ep for ep in result.endpoints if ep.name == endpoint_name), None)
    if not endpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint '{endpoint_name}' not found on API #{api_id}",
        )

    return {
        "name": endpoint.name,
        "description": endpoint.description,
        "fields": {
            fn: {
                "type": f.type,
                "description": f.description,
                "example": f.example,
            }
            for fn, f in endpoint.schema_fields.items()
        },
    }


@dashboard_app.get("/api/v1/{api_id}/{endpoint_name}/{item_id}", tags=["gateway"])
async def gateway_get_item(
    api_id: int,
    endpoint_name: str,
    item_id: int,
) -> dict[str, Any]:
    """Dynamic gateway single item endpoint by index ID."""
    result = await get_api(api_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"API #{api_id} not found")

    endpoint = next((ep for ep in result.endpoints if ep.name == endpoint_name), None)
    if not endpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint '{endpoint_name}' not found on API #{api_id}",
        )

    data = endpoint.sample_data
    if item_id < 0 or item_id >= len(data):
        raise HTTPException(
            status_code=404,
            detail=f"Item with index {item_id} not found on endpoint '{endpoint_name}'",
        )

    return {"data": data[item_id], "id": item_id}


@dashboard_app.get("/delete/{api_id}")
async def dashboard_delete_api(api_id: int):
    """Delete an API and redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    await delete_api(api_id)
    return RedirectResponse(url="/", status_code=302)


def run_dashboard(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the dashboard server."""
    import uvicorn
    uvicorn.run(dashboard_app, host=host, port=port, log_level="warning")
