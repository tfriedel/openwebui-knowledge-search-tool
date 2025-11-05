# Open WebUI Tools

A collection of custom tools for [Open WebUI](https://github.com/open-webui/open-webui) that extend its functionality with intelligent, on-demand features.

## Tools

### 📚 Knowledge Search Tool

Search organizational knowledge bases on-demand when the LLM determines it's needed, rather than constantly injecting context into every message.

**Features:**
- ✅ LLM intelligently decides when to access knowledge
- ✅ Token efficient - only retrieves when necessary
- ✅ Full citation support with inline [1], [2] references
- ✅ Works with existing Open WebUI knowledge bases
- ✅ No external dependencies or services required
- ✅ Supports multiple knowledge bases
- ✅ Direct database access (no API authentication issues)

**Use Case:** You want the main assistant to handle general chat normally, but be able to reference stored knowledge or documentation when the user asks questions that require internal data.

**[→ View Installation Guide](reddit_post.md)**

## Installation

### Prerequisites

- Open WebUI installed and running
- One or more Knowledge Bases created in Open WebUI

### Quick Start

1. **Copy the tool code**
   - Open `knowledge_search_tool.py`
   - Copy the entire contents

2. **Create the tool in Open WebUI**
   - Navigate to **Workspace → Tools**
   - Click **"Create Tool"**
   - Paste the code
   - Save

3. **Configure the tool**
   - Find your knowledge base IDs (see guide below)
   - Set `default_knowledge_bases` in tool settings
   - Adjust `top_k` and `relevance_threshold` if needed

4. **Enable for your models**
   - Go to **Workspace → Models**
   - Edit your model
   - Enable "Knowledge Search Tool" under Tools
   - Save

### Finding Knowledge Base IDs

**Method 1: Via URL**
1. Go to **Workspace → Knowledge**
2. Click on a knowledge base
3. The URL contains the ID: `http://localhost:8080/workspace/knowledge/[KNOWLEDGE_BASE_ID]`

**Method 2: Via the Tool**
1. Enable the tool on a model
2. Ask in chat: "List available knowledge bases"
3. The tool will show all knowledge bases with their IDs

## Usage Examples

### Example 1: Policy Question
```
User: What's our password policy?
LLM: [Calls search_knowledge("password policy")]
LLM: According to the security documentation [1], passwords must be
     at least 12 characters and include uppercase, lowercase, numbers,
     and special characters [2].
```

### Example 2: General Chat (No Knowledge Needed)
```
User: What's 2+2?
LLM: 4 (no knowledge search performed)
```

### Example 3: Technical Documentation
```
User: How do I deploy to production?
LLM: [Calls search_knowledge("deployment procedures")]
LLM: Based on the deployment guide [1], follow these steps:
     1. Run tests locally [1]
     2. Create a release branch [2]
     3. Deploy to staging first [1]
     ...
```

## Configuration

### Tool Valves (Settings)

| Setting | Description | Default |
|---------|-------------|---------|
| `default_knowledge_bases` | Comma-separated knowledge base IDs | `""` (empty) |
| `top_k` | Number of document chunks to retrieve | `5` |
| `relevance_threshold` | Minimum similarity score (0.0-1.0) | `0.0` |

**Example Configuration:**
```
default_knowledge_bases: "kb_policies,kb_technical,kb_hr"
top_k: 5
relevance_threshold: 0.0
```

## How It Works

1. **Tool Registration**: The LLM sees the tool as an available function
2. **Intelligent Decision**: When the user asks a relevant question, the LLM decides to call `search_knowledge(query)`
3. **Direct Retrieval**: The tool queries knowledge bases using Open WebUI's internal `query_collection()` function
4. **Citation Formatting**: Results are formatted with XML `<source>` tags (same as native RAG)
5. **LLM Response**: The LLM receives context and generates a response with inline citations [1], [2]
6. **UI Display**: Citations appear in the source panel, just like native knowledge bases

## Comparison: Tool vs. Native Knowledge

| Feature | Native Knowledge Base | Knowledge Search Tool |
|---------|----------------------|----------------------|
| Retrieval Timing | Every message | Only when LLM decides |
| Token Usage | High (always adds context) | Efficient (conditional) |
| LLM Intelligence | No | Yes |
| Citations | ✅ Yes | ✅ Yes |
| Source Panel | ✅ Yes | ✅ Yes |
| Multiple KB Search | One per model | Can search any combination |
| General Chat | Cluttered with context | Clean |

## Troubleshooting

### "Error: No knowledge bases specified"
**Solution:** Configure `default_knowledge_bases` in tool settings with your knowledge base IDs, or have the LLM pass the `knowledge_base_ids` parameter.

### "No relevant information found"
**Causes:**
- Query didn't match knowledge base content
- Knowledge base is empty or not properly configured
- Relevance threshold too high

**Solution:** Try different search terms or check knowledge base contents.

### Tool not being called
**Possible Issues:**
- Tool not enabled for the model
- LLM doesn't support function calling
- Query not clearly requiring knowledge base access

**Solution:**
- Verify tool is enabled in model settings
- Try explicit requests: "Search our documentation for..."
- Use a modern LLM that supports function calling

### 401 Unauthorized Error
**Solution:** This has been fixed in the current version. The tool now uses direct database access instead of API calls, eliminating authentication issues.

## Technical Details

### Architecture

The tool uses Open WebUI's internal modules:
- `open_webui.retrieval.utils.query_collection()` - Direct vector database querying
- `open_webui.models.knowledge.Knowledges` - Knowledge base database access
- `open_webui.models.users.Users` - User management
- `app.state.EMBEDDING_FUNCTION()` - Same embedding function as native RAG

### Why Not Pipelines or Filters?

We evaluated three approaches:

1. **Filter Functions** ❌
   - Run on every message
   - Would require keyword matching (too rigid)
   - Can't leverage LLM intelligence

2. **Pipelines with FunctionCallingBlueprint** ❌
   - Requires separate service deployment
   - Adds complexity and maintenance overhead
   - Extra latency from separate service calls

3. **Native Tools** ✅
   - Runs inside Open WebUI
   - LLM decides intelligently when to use
   - No external dependencies
   - Simple to install and maintain

## Contributing

Contributions are welcome! Feel free to:
- Report issues
- Suggest improvements
- Submit pull requests
- Share your use cases

## License

MIT License - feel free to use and modify as needed.

## Related Resources

- [Open WebUI Documentation](https://docs.openwebui.com/)
- [Open WebUI GitHub](https://github.com/open-webui/open-webui)
- [Open WebUI Tools Documentation](https://docs.openwebui.com/features/plugin/tools/)
- [Reddit Discussion Post](reddit_post.md)

## Acknowledgments

This tool leverages Open WebUI's internal retrieval system and citation framework to provide seamless integration with existing knowledge bases.

---

**Need help?** Open an issue or join the [Open WebUI Discord](https://discord.gg/5rJgQTnV4s)
