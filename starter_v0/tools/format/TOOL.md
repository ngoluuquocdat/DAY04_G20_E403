---
name: format
track: core
kind: local_formatter
requires_env: []
inputs: [items, template, headline]
outputs: [markdown, item_count]
side_effect: false
---
# format_data_to_markdown

Formats already-collected items into a markdown digest. It does not fetch data.
