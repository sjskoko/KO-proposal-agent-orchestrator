"""Web research skill handler."""

from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger(__name__)


def run(inputs: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """
    Entry point called by the skill runner.

    Args:
        inputs: Validated inputs matching skill.yaml input schema
        context: AgentContext providing access to runtimes and model

    Returns:
        Dict matching the skill.yaml output schema
    """
    query = inputs["query"]
    max_sources = inputs.get("max_sources", 5)
    output_format = inputs.get("output_format", "summary")

    log.info("skill.web_research.start", query=query, max_sources=max_sources)

    sources = _fetch_sources(query, max_sources, context)
    if not sources:
        return {"summary": f"No results found for: {query}", "sources": []}

    summary = _synthesize(query, sources, output_format, context)
    return {"summary": summary, "sources": sources}


def validate_inputs(inputs: dict) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors = []
    if not inputs.get("query", "").strip():
        errors.append("'query' must be a non-empty string")
    max_s = inputs.get("max_sources", 5)
    if not isinstance(max_s, int) or max_s < 1 or max_s > 20:
        errors.append("'max_sources' must be an integer between 1 and 20")
    return errors


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _fetch_sources(query: str, max_sources: int, context) -> list[dict]:
    """Use ApiRuntime to search and fetch source content."""
    sources = []

    # If context provides runtime access, use it; otherwise return stub
    if context is None:
        log.warning("skill.web_research.no_context — returning stub sources")
        return [{"url": "https://example.com", "title": "Example", "snippet": query}]

    # Attempt search via api runtime
    try:
        api_runtime = context.get_runtime("api")
        from core.runtime.base import RuntimeCall
        result = api_runtime.execute(RuntimeCall(
            runtime_id="api",
            operation="http_get",
            params={
                "url": f"https://ddg-api.herokuapp.com/search?q={query}&max_results={max_sources}",
            },
        ))
        if result.success:
            import json
            data = json.loads(result.data.get("body", "[]"))
            for item in data[:max_sources]:
                sources.append({
                    "url": item.get("href", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("body", ""),
                })
    except Exception as exc:
        log.error("skill.web_research.fetch_error", error=str(exc))

    return sources


def _synthesize(query: str, sources: list[dict], output_format: str, context) -> str:
    """Use the model to synthesize research results."""
    if context is None:
        return "\n".join(s["snippet"] for s in sources)

    snippets = "\n\n".join(
        f"Source: {s['title']} ({s['url']})\n{s['snippet']}" for s in sources
    )
    prompt = (
        f"Research question: {query}\n\n"
        f"Sources:\n{snippets}\n\n"
        f"Provide a {output_format.replace('_', ' ')} of the above research."
    )
    try:
        from core.model.base import Message, ModelOptions
        model = context.get_model()
        response = model.complete([Message(role="user", content=prompt)], ModelOptions(temperature=0.3))
        return response.content
    except Exception as exc:
        log.error("skill.web_research.synthesize_error", error=str(exc))
        return snippets
