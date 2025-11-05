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
