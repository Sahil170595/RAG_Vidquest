import spacy
from pymongo import MongoClient
from tqdm import tqdm

nlp = spacy.load("en_core_web_sm")
client = MongoClient("mongodb://localhost:27017/")
db = client["video_rag"]
sub_col = db["subtitles"]
merged_col = db["merged_sentences"]

MERGE_WORD_LIMIT = 50


def merge_sentences():
    merged_col.drop()

    for doc in tqdm(sub_col.find(), desc="🔄 Merging subtitles"):
        video_key = doc["video_key"]
        sentences = []
        buffer = ""
        ts_start, ts_end = None, None

        for segment in doc["subtitles"]:
            segment_text = segment["text"].strip().replace("\n", " ")
            doc_spacy = nlp(segment_text)
            for sent in doc_spacy.sents:
                sent_text = sent.text.strip()
                if not sent_text:
                    continue

                if not buffer:
                    ts_start = segment["start"]

                buffer += " " + sent_text
                ts_end = segment["end"]

                if len(buffer.split()) >= MERGE_WORD_LIMIT:
                    sentences.append({
                        "text": buffer.strip(),
                        "timestamp": {"start": ts_start, "end": ts_end}
                    })
                    buffer = ""

        if buffer:
            sentences.append({
                "text": buffer.strip(),
                "timestamp": {"start": ts_start, "end": ts_end}
            })

        merged_col.insert_one({
            "video_key": video_key,
            "sentences": sentences
        })

    print(f"✅ Merged subtitles inserted into 'merged_sentences' collection")


if __name__ == "__main__":
    merge_sentences()
