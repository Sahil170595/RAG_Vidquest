
from preprocessing.subtitle_extractor import extract_and_store_subtitles_from_dataset
from preprocessing.question_generator import generate_questions_for_all
from preprocessing.frame_extractor import extract_all_frames_from_dataset
from preprocessing.merger import merge_subtitle_segments
from embeddings.topic_modeling import generate_and_store_embeddings

DATASET_DIR = r"C:\Users\sahil\Downloads\AIVideos\processed_data"
SUBTITLE_OUTPUT = r"C:\Users\sahil\Downloads\AIVideos\subtitles_output"
FRAME_OUTPUT = r"C:\Users\sahil\Downloads\AIVideos\frames_output"

if __name__ == "__main__":
    print("🔹 Step 1: Extracting subtitles")
    extract_and_store_subtitles_from_dataset(DATASET_DIR, SUBTITLE_OUTPUT)

    print("🔹 Step 2: Generating questions")
    generate_questions_for_all()

    print("🔹 Step 3: Extracting frames")
    extract_all_frames_from_dataset(DATASET_DIR, FRAME_OUTPUT)

    print("🔹 Step 4: Merging segments")
    merge_subtitle_segments()

    print("🔹 Step 5: Generating embeddings and uploading to Qdrant")
    generate_and_store_embeddings()

    print("✅ All preprocessing steps complete.")
