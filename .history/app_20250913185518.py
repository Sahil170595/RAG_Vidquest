import gradio as gr
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from backend.ollama_summarizer import summarize_with_ollama
from backend.qdrant_retriever import query_qdrant
from backend.utils import find_video_path, slice_clip
import os

# Load model and setup
model = SentenceTransformer("all-MiniLM-L6-v2")
qdrant = QdrantClient(host="localhost", port=6333)

def respond(query):
    embedding = model.encode(query).tolist()
    results = query_qdrant(qdrant, embedding)

    if not results:
        return query, "No matches found.", "N/A", None

    # Chain of Thoughts
    thoughts = "\n\n".join([f"{i+1}. {r.payload['text']}" for i, r in enumerate(results)])

    # Summary via Ollama
    summary = summarize_with_ollama(thoughts, query)

    # Clip slicing
    top = results[0].payload
    video_key = top["video_key"]
    video_path = find_video_path(video_key)
    clip_path = os.path.join("clips_output", f"{video_key}_clip.mp4")

    if video_path and not os.path.exists(clip_path):
        clip_path = slice_clip(video_path, top["start"], top["end"], clip_path)

    return query, thoughts, summary, clip_path

demo = gr.Interface(
    fn=respond,
    inputs=gr.Textbox(label="Ask a question based on the videos"),
    outputs=[
        gr.Textbox(label="Question"),
        gr.Textbox(label="Chain of Thoughts (Transcript Matches)"),
        gr.Textbox(label="Final Answer (Summarized by Ollama)"),
        gr.Video(label="Relevant Video Clip", format="mp4")
    ],
    title="🎓 AI Video Chat Assistant",
    description="Ask a question. See transcript matches, a smart summary, and watch the related clip."
)

if __name__ == "__main__":
    demo.launch()
