from mcp.server.fastmcp import FastMCP
from ksdb.client import Client
import os

# Initialize FastMCP
mcp = FastMCP("KSdb")

# Initialize KSdb Client
# We assume the server is running locally
client = Client(url=os.getenv("KSDB_URL", "http://127.0.0.1:8000"))

@mcp.resource("ksdb://{collection_name}")
def list_documents(collection_name: str) -> str:
    """List all document IDs in a collection"""
    try:
        col = client.get_collection(collection_name)
        # We don't have a list_docs method in client yet, so we do a dummy query or add one
        # For now, let's just return a message or implement list_docs in client
        # Actually, let's just return a summary
        return f"Collection: {collection_name}\n(Listing all docs not yet supported in API)"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search(collection_name: str, query: str, k: int = 5) -> str:
    """
    Search for documents in KSdb using Hybrid Search (Vector + Keyword).
    """
    try:
        col = client.get_collection(collection_name)
        results = col.query(query_texts=[query], n_results=k)
        
        output = []
        for i, (doc, meta, dist) in enumerate(zip(results["documents"][0], results["metadatas"][0], results["distances"][0])):
            output.append(f"--- Result {i+1} (Score: {dist:.4f}) ---\n{doc}\nMetadata: {meta}")
            
        return "\n\n".join(output)
    except Exception as e:
        return f"Error searching: {str(e)}"

@mcp.tool()
def add_document(collection_name: str, doc_id: str, text: str, metadata: str = "{}") -> str:
    """
    Add a document to KSdb.
    """
    try:
        import json
        meta_dict = json.loads(metadata)
        col = client.get_or_create_collection(collection_name)
        col.add(ids=[doc_id], documents=[text], metadatas=[meta_dict], deduplicate=True, extract_graph=True)
        return f"Successfully added document '{doc_id}' to '{collection_name}'"
    except Exception as e:
        return f"Error adding document: {str(e)}"

@mcp.tool()
def query_graph(collection_name: str, entity: str) -> str:
    """
    Query the Knowledge Graph for an entity.
    """
    try:
        col = client.get_collection(collection_name)
        results = col.query_graph(entities=[entity])
        
        if not results:
            return f"No knowledge found for '{entity}'"
            
        output = [f"Knowledge about '{entity}':"]
        for triple in results:
            output.append(f"- {triple['subject']} {triple['predicate']} {triple['object']}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error querying graph: {str(e)}"

if __name__ == "__main__":
    mcp.run()
