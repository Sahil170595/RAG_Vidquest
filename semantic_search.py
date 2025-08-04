from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from config import QDRANT_HOST, QDRANT_PORT

# Load model and Qdrant client
model = SentenceTransformer("all-MiniLM-L6-v2")
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

def search_similar_sentences(query, top_k=3):
    embedding = model.encode(query).tolist()

    results = qdrant.search(
        collection_name="video_embeddings",
        query_vector=embedding,
        limit=top_k
    )

    matches = []
    for res in results:
        payload = res.payload
        matches.append({
            "text": payload["text"],
            "video_key": payload["video_key"],
            "start": payload["start"],
            "end": payload["end"]
        })

    return matches
