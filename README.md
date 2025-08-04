### 🗂️ `README.md` 


# 🎓 AI Video Chat Assistant

A Retrieval-Augmented Generation (RAG) system for querying course lecture videos. Users can ask natural language questions and receive relevant video clips, transcripts, and summaries grounded directly in the lecture content.

# Architecture

* ![image](https://github.com/user-attachments/assets/54865242-10b5-4448-a710-3e42a867d370)

---

## 🚀 Demo

Launch the Gradio app and try queries like:

“Using only the videos, explain how ResNets work.”
“Using only the videos, explain the advantages of CNNs over fully connected networks.”
“Using only the videos, explain the the binary cross entropy loss function.”
---

## 🧱 Project Architecture

- **ETL Pipeline**: Extracts frames and aligns them with subtitles.
- **Featurization**: Embeds merged sentences with `SentenceTransformer`.
- **Vector Search**: Qdrant for nearest neighbor lookup.
- **Summarization**: Uses `Ollama` (Gemma 3) to summarize the top transcript matches.
- **Frontend**: Gradio app for interactive querying and video playback.

---

## 📁 Directory Structure

```

video-chat-assistant/
├── app/                  # Gradio UI and logic
├── data/                 # Small sample inputs
├── etl/                  # Subtitle/frame extraction scripts
├── vector\_db/            # Qdrant upload scripts
├── notebooks/            # Exploration & testing
├── clips\_output/         # Output clips (small samples only)
├── requirements.txt
└── README.md

````

---

## 📦 Full Dataset Access

Due to GitHub file limits, full video data is **not included**. To test on complete data:

1. Download from https://huggingface.co/datasets/aegean-ai/ai-lectures-spring-24

---


Make sure MongoDB and Qdrant are running, then run:

```bash
python app/main.py  # or open the notebook to launch
```

---

## 📊 Example Outputs

| Query              | Summary                 | Clip |
| ------------------ | ----------------------- | ---- |
| What is padding?   | A padded convolution... | ✅    |
| ResNet motivation? | Skipping connections... | ✅    |

---

```markdown
# 📦 Dataset Setup Guide

This project uses a collection of lecture videos and their subtitles in `.vtt` format.

---

## Option 1: Manual Download

Download the raw dataset (videos + subtitles) here:

🔗 [Google Drive - Video Dataset](https://your-drive-link)

Place them in the following structure:
````

data/
└── videos/
├── xyz123.mp4
├── xyz123.vtt
└── ...

````

---

## Option 2: Rebuild from Raw Files

Run the subtitle and frame extraction:

```bash
python etl/extract_subtitles.py
python etl/extract_frames.py
````

MongoDB must be running and populated with aligned subtitle data for this to work.

---

## Output Samples

* `output/`: contains `.mp4` slices of relevant segments
* ![image](https://github.com/user-attachments/assets/df5d3601-fa88-4410-9e53-14b3d3eb4fe6)


