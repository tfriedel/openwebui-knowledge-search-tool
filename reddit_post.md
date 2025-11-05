# Solution: On-Demand Knowledge Base Access in Open WebUI

I had the same need - wanting the LLM to access organizational knowledge **only when relevant**, not constantly injecting context into every message. Here's how I solved it:

## The Problem with Native Knowledge Bases

When you attach a knowledge base to a model in Open WebUI, it:
- ✅ Works great for citations and retrieval
- ❌ **Always** retrieves context on every single message
- ❌ Wastes tokens on conversations that don't need organizational knowledge
- ❌ No conditional logic - it's all or nothing

## The Solution: Create a Knowledge Search Tool

Instead of attaching knowledge to the model, create a **Tool** that the LLM can call when it decides knowledge is needed. This gives you:

✅ **LLM decides** when to access knowledge (not keyword matching)
✅ **Token efficient** - only retrieves when necessary
✅ **Full citations** - same citation UI as native knowledge bases
✅ **Flexible** - can search specific knowledge bases or all of them
✅ **Zero external dependencies** - runs inside Open WebUI

## How to Implement It

### Step 1: Create the Tool

1. Go to **Workspace → Tools** in Open WebUI
2. Click **"Create Tool"**
3. Paste this code:

```python
"""
title: Knowledge Search Tool
author: Your Name
author_url: https://yourwebsite.com
git_url: https://github.com/yourname/knowledge-search-tool
description: Search organizational knowledge bases on demand when the LLM determines it's needed
required_open_webui_version: 0.4.0
requirements:
version: 1.0.0
licence: MIT
"""

import asyncio
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Import Open WebUI internal modules for direct access
from open_webui.retrieval.utils import query_collection
from open_webui.models.knowledge import Knowledges
from open_webui.models.users import Users


class Tools:
    def __init__(self):
        """Initialize the Knowledge Search Tool."""
        self.citation = False  # Enable manual citation control
        self.valves = self.Valves()

    class Valves(BaseModel):
        """Configuration for the Knowledge Search Tool."""
        default_knowledge_bases: str = Field(
            default="",
            description="Comma-separated default knowledge base IDs to search (leave empty to require specification)"
        )

        top_k: int = Field(
            default=5,
            description="Number of relevant chunks to retrieve"
        )

        relevance_threshold: float = Field(
            default=0.0,
            description="Minimum relevance score (0.0-1.0)"
        )

    async def search_knowledge(
        self,
        query: str,
        knowledge_base_ids: Optional[str] = None,
        __event_emitter__=None,
        __user__: dict = None,
    ) -> str:
        """
        Search organizational knowledge bases for relevant information.

        Use this tool when the user asks questions about:
        - Internal documentation, policies, or procedures
        - Technical specifications or guidelines
        - Organizational knowledge or best practices
        - Any topic that might be covered in the knowledge base

        :param query: The search query describing what information to find
        :param knowledge_base_ids: Optional comma-separated knowledge base IDs to search (e.g., "kb_policies,kb_docs"). If not provided, searches default knowledge bases.
        :return: Retrieved information with source citations
        """

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "Searching knowledge bases...",
                    "done": False
                }
            })

        try:
            # Determine which knowledge bases to search
            if knowledge_base_ids:
                kb_ids = [kb.strip() for kb in knowledge_base_ids.split(",")]
            elif self.valves.default_knowledge_bases:
                kb_ids = [kb.strip() for kb in self.valves.default_knowledge_bases.split(",")]
            else:
                return "Error: No knowledge bases specified. Please provide knowledge_base_ids parameter or configure default knowledge bases in tool settings."

            # Get user for embedding function (if needed)
            user_obj = None
            if __user__ and __user__.get("id"):
                user_obj = Users.get_user_by_id(__user__["id"])

            # Import the embedding function from the request context
            # Note: This requires the tool to have access to request.app.state
            from open_webui.main import app

            embedding_function = lambda queries, prefix="": app.state.EMBEDDING_FUNCTION(
                queries, prefix=prefix, user=user_obj
            )

            # Use internal retrieval function directly
            result = query_collection(
                collection_names=kb_ids,
                queries=[query],
                embedding_function=embedding_function,
                k=self.valves.top_k,
            )

            # Process the results
            if not result or not result.get("documents") or not result["documents"][0]:
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {
                            "description": "No relevant knowledge found",
                            "done": True
                        }
                    })
                return f"No relevant information found in the knowledge bases for query: '{query}'"

            documents = result["documents"][0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]

            # Format results with XML source tags (like native RAG)
            formatted_context = ""

            for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                citation_id = i + 1
                source_name = metadata.get("source", f"Source {citation_id}")

                # Emit citation for UI
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "citation",
                        "data": {
                            "document": [doc],
                            "metadata": [{
                                "source": source_name,
                                "file_id": metadata.get("file_id", ""),
                                "relevance_score": round(distance, 3)
                            }],
                            "source": {
                                "name": source_name,
                                "url": f"#file-{metadata.get('file_id', '')}"
                            }
                        }
                    })

                # Format with XML tags for inline citations
                formatted_context += f'<source id="{citation_id}" name="{source_name}">{doc}</source>\n\n'

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"Found {len(documents)} relevant documents",
                        "done": True
                    }
                })

            # Return formatted response with instructions for citations
            return f"""Here is the relevant information from the knowledge bases:

<context>
{formatted_context.strip()}
</context>

Use the information above to answer the user's question. When referencing specific information, include inline citations using [1], [2], etc., corresponding to the source IDs in the <source> tags. Do not include the XML tags in your response."""

        except Exception as e:
            error_msg = f"Error searching knowledge bases: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": error_msg,
                        "done": True
                    }
                })
            return error_msg

    async def list_available_knowledge_bases(
        self,
        __event_emitter__=None,
        __user__: dict = None,
    ) -> str:
        """
        List all knowledge bases available to search.

        Use this tool when you need to discover which knowledge bases exist
        and their IDs before searching them.

        :return: List of available knowledge bases with their IDs and descriptions
        """

        try:
            # Get knowledge bases directly from the database
            if __user__ and __user__.get("id"):
                knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
                    __user__["id"],
                    permission="read"
                )
            else:
                knowledge_bases = Knowledges.get_knowledge_bases()

            if not knowledge_bases:
                return "No knowledge bases are currently available."

            # Format the list
            kb_info = ["Available knowledge bases:\n"]
            for kb in knowledge_bases:
                kb_data = kb.data or {}
                file_count = len(kb_data.get("file_ids", []))
                kb_info.append(
                    f"- **{kb.name}** (ID: `{kb.id}`)\n"
                    f"  Description: {kb.description or 'No description'}\n"
                    f"  Files: {file_count}"
                )

            return "\n".join(kb_info)

        except Exception as e:
            return f"Error listing knowledge bases: {str(e)}"
```

4. Click **Save**

### Step 2: Find Your Knowledge Base IDs

You need the IDs of the knowledge bases you want to search:

**Option A: Via UI**
1. Go to **Workspace → Knowledge** in Open WebUI
2. Click on a knowledge base
3. Look at the URL: `http://localhost:8080/workspace/knowledge/[THIS_IS_THE_ID]`
4. Or the ID might be visible in the knowledge base details

**Option B: Use the Tool Itself**
1. Enable the tool (see Step 3)
2. In a chat, ask: "List available knowledge bases"
3. The LLM will call `list_available_knowledge_bases()` and show you all IDs

### Step 3: Configure the Tool

1. In **Workspace → Tools**, click on your "Knowledge Search Tool"
2. Go to **Settings** or **Valves**
3. Set `default_knowledge_bases` to your comma-separated KB IDs:
   - Example: `kb_policies,kb_technical,kb_procedures`
   - Or leave empty to require the LLM to specify which KB to search
4. Adjust `top_k` (number of chunks) if needed
5. Save

### Step 4: Enable the Tool for Your Models

1. Go to **Workspace → Models**
2. Edit the model(s) you want to use this with
3. Scroll to the **Tools** section
4. Enable "Knowledge Search Tool"
5. Save

### Step 5: Test It

Start a conversation and ask questions that should trigger knowledge retrieval:

**Example 1:**
- **You:** "What's our company's password policy?"
- **LLM:** *Decides to call `search_knowledge("password policy")`*
- **Tool:** *Returns relevant docs with citations*
- **LLM:** "According to the security documentation [1], passwords must be at least 12 characters and include..."

**Example 2:**
- **You:** "What's the weather like?" *(doesn't need knowledge)*
- **LLM:** *Doesn't call the tool, responds normally*

**Example 3:**
- **You:** "Tell me about our deployment procedures"
- **LLM:** *Calls `search_knowledge("deployment procedures")`*
- **Tool:** *Returns relevant docs*
- **LLM:** "Based on the technical documentation [1][2], deployments follow this process..."

## How It Works

1. **The LLM sees the tool** as an available function with a clear description
2. **When appropriate**, the LLM decides to call `search_knowledge(query)`
3. **The tool queries your knowledge bases** using Open WebUI's internal retrieval system
4. **Results are formatted with XML source tags** (same as native RAG)
5. **The LLM receives the context** and generates a response with inline citations like [1], [2]
6. **The UI shows citations** in the source panel, just like native knowledge bases

## Key Benefits Over Native Knowledge Bases

| Feature | Native Knowledge | This Tool |
|---------|------------------|-----------|
| **Token Usage** | Every message | Only when needed |
| **LLM Decision** | No | Yes |
| **Citations** | ✅ Yes | ✅ Yes |
| **Source Panel** | ✅ Yes | ✅ Yes |
| **Flexible Targeting** | Per-model only | Can search different KBs per query |
| **General Chat** | Always adds context | Clean, no unnecessary context |

## Troubleshooting

**"Error: No knowledge bases specified"**
- Configure `default_knowledge_bases` in tool settings, OR
- The LLM needs to pass the `knowledge_base_ids` parameter

**"No relevant information found"**
- The query didn't match anything in your knowledge bases
- Try different search terms or check if your knowledge base has the relevant documents

**Tool doesn't appear to be called**
- Make sure the tool is enabled for your model
- Try being more explicit: "Search our documentation for..."
- Check that your LLM supports function calling (most modern models do)

## Why This Approach is Better Than Pipelines or Filters

I explored several options:

1. **Filter Functions**: Would run on every message and need keyword matching (too rigid)
2. **Pipelines with FunctionCallingBlueprint**: Requires separate service deployment (too complex)
3. **This Tool Approach**: ✅ Simple, runs inside Open WebUI, LLM decides intelligently

## Credits

This tool uses Open WebUI's internal retrieval functions (`query_collection`) to access knowledge bases directly, bypassing the need for API authentication. It formats results with the same citation system as native RAG, giving you the best of both worlds.

Hope this helps others who want smarter, on-demand knowledge access!
