from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance

# Load sentence embedding model and Qdrant vector DB client
model = SentenceTransformer("all-MiniLM-L6-v2")
qdrant = QdrantClient(host="localhost", port=6333)

def search_similar_sentences(query, top_k=3):
    embedding = model.encode(query).tolist()
    results = qdrant.search(
        collection_name="video_embeddings",
        query_vector=embedding,
        limit=top_k
    )
    return results
