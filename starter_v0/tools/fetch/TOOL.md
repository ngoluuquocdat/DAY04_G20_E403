---
name: fetch
track: core
kind: live_api
provider: Firecrawl
requires_env: [FIRECRAWL_API_KEY]
inputs: [url]
outputs: [items]
side_effect: false
---
# read_webpage_content

Reads the content of a single URL via Firecrawl.
