# Open WebUI Knowledge Search Tool

On-demand knowledge base search tool for [Open WebUI](https://github.com/open-webui/open-webui). The LLM intelligently decides when to access organizational knowledge instead of constantly injecting context into every message.

## Features

- LLM decides when to access knowledge bases
- Token efficient - only retrieves when necessary
- Full citation support with inline [1], [2] references
- Works with existing Open WebUI knowledge bases
- No external dependencies required
- Supports multiple knowledge bases

## Installation

1. Copy the contents of `knowledge_search_tool.py`
2. In Open WebUI, go to **Workspace → Tools** → **Create Tool**
3. Paste the code and save
4. Configure `default_knowledge_bases` with your knowledge base IDs (comma-separated)
5. Go to **Workspace → Models** → Edit your model → Enable the tool

### Finding Knowledge Base IDs

Go to **Workspace → Knowledge**, click on a knowledge base, and check the URL:
```
http://localhost:8080/workspace/knowledge/[KNOWLEDGE_BASE_ID]
```

Alternatively, enable the tool and ask: "List available knowledge bases"

## Usage

When users ask questions requiring organizational knowledge, the LLM automatically calls `search_knowledge()`:

```
User: What's our password policy?
LLM: According to the security documentation [1], passwords must be at least
     12 characters and include uppercase, lowercase, numbers, and special
     characters [2].
```

For general questions, the tool is not invoked:
```
User: What's 2+2?
LLM: 4
```

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `default_knowledge_bases` | Comma-separated knowledge base IDs | `""` |
| `top_k` | Number of document chunks to retrieve | `5` |
| `relevance_threshold` | Minimum similarity score (0.0-1.0) | `0.0` |

## How It Works

1. The LLM sees the tool as an available function
2. When a question requires knowledge, the LLM calls `search_knowledge(query)`
3. The tool queries knowledge bases using Open WebUI's internal `query_collection()`
4. Results are formatted with XML `<source>` tags (same as native RAG)
5. The LLM generates a response with inline citations [1], [2]
6. Citations appear in the source panel

## Comparison: Tool vs. Native Knowledge

| Feature | Native Knowledge | This Tool |
|---------|------------------|-----------|
| Retrieval | Every message | Only when needed |
| Token Usage | High | Efficient |
| LLM Decision | No | Yes |
| Citations | Yes | Yes |
| Multiple KBs | One per model | Any combination |

## Troubleshooting

**"Error: No knowledge bases specified"**
Configure `default_knowledge_bases` in tool settings or have the LLM pass the `knowledge_base_ids` parameter.

**"No relevant information found"**
The query didn't match knowledge base content. Try different search terms.

**Tool not being called**
- Verify tool is enabled in model settings
- Ensure your LLM supports function calling
- Try explicit requests: "Search our documentation for..."

## Technical Details

The tool uses Open WebUI's internal modules:
- `open_webui.retrieval.utils.query_collection()` - Direct vector database querying
- `open_webui.models.knowledge.Knowledges` - Knowledge base access
- `app.state.EMBEDDING_FUNCTION()` - Same embedding function as native RAG

This approach is simpler than pipelines (no separate service) and more intelligent than filters (LLM decides vs keyword matching).

## License

MIT License

## Resources

- [Open WebUI Documentation](https://docs.openwebui.com/)
- [Open WebUI GitHub](https://github.com/open-webui/open-webui)
- [Tools Documentation](https://docs.openwebui.com/features/plugin/tools/)
