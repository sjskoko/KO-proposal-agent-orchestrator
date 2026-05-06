# Web Research Skill

## Purpose
This skill performs structured web research by querying search engines, fetching relevant
pages, and synthesizing the content into a useful output.

## When to use
- When the agent needs up-to-date information not available in its training data
- When the goal requires facts, citations, or external context
- When researching a person, company, topic, or event

## How it works

1. Parse the `query` input
2. Use the `api` or `browser` runtime to perform a web search
3. Fetch content from the top `max_sources` results
4. Use the `reasoning` runtime to synthesize and summarize findings
5. Return the structured output including `summary` and `sources`

## Output format options
- `summary` — a paragraph summary of all findings
- `bullet_points` — key findings as a bulleted list
- `structured` — JSON with topic, key facts, and sources

## Limitations
- Respects `allowed_domains` from the `api` runtime configuration
- Does not follow more than 2 redirect hops per URL
- Skips paywalled content automatically

## Error handling
- If fewer than `max_sources` results are found, returns what is available
- If a source fetch fails, logs the error and continues with remaining sources
- If no results are found, returns an empty summary with an explanation
