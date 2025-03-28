"""Youtube timestamp filtering using Google"""
# %%
import os
import re
import time
from patlib import Path
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# --- Configuration ---
VIDEO_URL = "https://www.youtube.com/watch?v=Sx0J7dIlL7c" # Replace with your target video URL
OUTPUT_FILENAME = Path("./tmp/filtered_transcript_google.md").resolve()
MODEL_NAME = "gemini-1.5-pro-latest" # Or whichever model you prefer

# Chunking Strategy: Aim for chunks of roughly this many source transcript lines.
# Adjust based on video length and density. Too small = many API calls; too large = context limits.
LINES_PER_CHUNK = 150
# Overlap: Number of lines from the end of the previous chunk to include at the start of the next.
# Helps the AI maintain context across boundaries.
OVERLAP_LINES = 10

# --- API Key ---
try:
    GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
    genai.configure(api_key=GOOGLE_API_KEY)
except KeyError:
    print("🛑 Error: GOOGLE_API_KEY environment variable not set.")
    print("Please set the environment variable and try again.")
    exit(1)
except Exception as e:
    print(f"🛑 Error configuring Google AI: {e}")
    exit(1)

# --- Prompt Template ---
# This is the modified prompt focusing on filtering
PROMPT_TEMPLATE = """
You are a specialized assistant focused on processing segments of YouTube video transcripts. Your primary goal is to intelligently filter timestamps, retaining only those marking logical breaks in speech, while performing minor corrections.

## Context
You are processing a *segment* of a longer video transcript. Process this segment assuming it connects logically to previous and subsequent segments. Make filtering decisions based on the content within *this segment*. The segment might start or end mid-paragraph or mid-sentence; apply the rules as best as possible.

## Core Task: Timestamp Filtering and Minor Correction
1.  **Input:** The input contains text interspersed with frequent YouTube timestamps (e.g., `[HH:MM:SS] Text...`).
2.  **Timestamp Goal:** Modify the text and timestamps so that timestamps primarily mark the beginning of:
    *   A new speaker's turn.
    *   A new "sentence" or, preferably, a new "paragraph" (a distinct thought or topic block) by the *same* speaker.
3.  **Timestamp Action:** *Delete* timestamps that do not meet these criteria. Merge the text previously separated by the deleted timestamps.
4.  **Timestamp Preference:** Aim for paragraph-length intervals between timestamps for a single speaker, unless interrupted or significant topic shift. Avoid timestamps mid-sentence or for minor pauses.
5.  **Correction Goal:** Correct obvious transcription errors based on context *within this segment*, especially technical terms, software names, etc.
6.  **Correction Constraint:** Prioritize accurate timestamp filtering. If unsure about a correction, keep original text. Do *not* summarize or paraphrase.
7.  **Result:** Output a continuous text flow for this segment, punctuated only by logically placed, correctly formatted timestamps, with minor errors fixed.

## Timestamp Formatting
-   Retain the *original time* of kept timestamps.
-   Format kept timestamps as clickable YouTube markdown links: `[[HH:MM:SS](BASE_YOUTUBE_URL&t=SSSs)]`
-   Replace `BASE_YOUTUBE_URL` with the specific URL provided below.
-   Calculate `SSS` as total seconds (HH*3600 + MM*60 + SS).

## Output Structure
Produce *only* the filtered and corrected timestamped transcript segment. Do **NOT** include any other sections, introductions, explanations, or markdown formatting like ```markdown ... ```.

## Processing Instructions

**Base YouTube URL:** `{base_url}`

**Process the following transcript segment:**

{transcript_segment}
"""

# --- Helper Functions ---

def get_video_id(url):
    """Extracts YouTube video ID from various URL formats."""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    print(f"🛑 Warning: Could not extract video ID from URL: {url}")
    return None

def format_seconds(seconds):
    """Converts seconds to HH:MM:SS format."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def calculate_seconds(hhmmss):
    """Converts HH:MM:SS string to total seconds."""
    parts = list(map(int, hhmmss.split(':')))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 1:
        return parts[0]
    return 0

def fetch_transcript(video_id):
    """Fetches transcript using youtube-transcript-api."""
    print(f"Fetching transcript for video ID: {video_id}...")
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Try fetching manual first, then generated
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            print("Using manually created transcript.")
        except NoTranscriptFound:
            print("No manual transcript found, trying generated...")
            transcript = transcript_list.find_generated_transcript(['en'])
            print("Using auto-generated transcript.")

        return transcript.fetch() # Returns list of dicts [{'text': '...', 'start': ..., 'duration': ...}]
    except TranscriptsDisabled:
        print(f"🛑 Error: Transcripts are disabled for video: {video_id}")
        return None
    except NoTranscriptFound:
        print(f"🛑 Error: No English transcript found for video: {video_id}")
        return None
    except Exception as e:
        print(f"🛑 Error fetching transcript: {e}")
        return None

def format_raw_transcript(transcript_data):
    """Formats the raw transcript list into a single string with [HH:MM:SS] timestamps."""
    formatted_lines = []
    for entry in transcript_data:
        timestamp = format_seconds(entry['start'])
        text = entry['text'].strip().replace('\n', ' ') # Clean up text a bit
        if text: # Only add lines with actual text
             formatted_lines.append(f"[{timestamp}] {text}")
    return "\n".join(formatted_lines)

def chunk_transcript(full_transcript_text, lines_per_chunk, overlap_lines):
    """Splits the formatted transcript into overlapping chunks."""
    lines = full_transcript_text.splitlines()
    if not lines:
        return []

    chunks = []
    start_index = 0
    while start_index < len(lines):
        end_index = min(start_index + lines_per_chunk, len(lines))
        chunk_lines = lines[start_index:end_index]
        chunks.append("\n".join(chunk_lines))

        # Move start_index for the next chunk, considering overlap
        start_index += lines_per_chunk - overlap_lines
        # Ensure start_index doesn't go backward or stay stuck if overlap >= chunk size
        start_index = max(start_index, end_index - overlap_lines + 1) if overlap_lines < lines_per_chunk else end_index

    # Basic validation: Ensure the last chunk reaches the end
    if chunks and not chunks[-1].endswith(lines[-1]):
         # This logic might slightly adjust the last chunk if overlap calculation fell short
         last_chunk_start_line_index = 0
         if len(chunks) > 1:
             # Find where the second to last chunk ended to estimate where the last should start
             # This is approximate as lines might change length
             approx_prev_end_line_num = (len(chunks) - 1) * (lines_per_chunk - overlap_lines)
             last_chunk_start_line_index = max(0, approx_prev_end_line_num)

         final_lines = lines[last_chunk_start_line_index:]
         if final_lines: # Make sure there are lines to add
             chunks[-1] = "\n".join(final_lines) # Replace last chunk with one that definitely goes to the end


    print(f"Split transcript into {len(chunks)} chunks.")
    return chunks

def call_gemini_api(segment, base_url):
    """Sends a chunk to the Gemini API and returns the filtered result."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = PROMPT_TEMPLATE.format(base_url=base_url, transcript_segment=segment)

    # API Call with retries for potential transient errors
    max_retries = 3
    delay = 5 # seconds
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                # Optional: Add safety settings if needed
                # safety_settings=[
                #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                # ]
                 generation_config=genai.types.GenerationConfig(
                    # candidate_count=1, # Default is 1
                    # stop_sequences=['\n\n\n'], # Optional: If needed
                    # max_output_tokens=..., # Careful with this, might cut off output
                    temperature=0.2 # Lower temperature for more deterministic filtering
                 )
            )
            # Simple check if response has expected text part
            if response.parts:
                return response.text.strip()
            else:
                # Handle cases where the response might be blocked or empty
                print(f"⚠️ Warning: API response for a chunk was empty or potentially blocked.")
                print(f"Prompt Feedback: {response.prompt_feedback}")
                return "" # Return empty string for this chunk

        except Exception as e:
            print(f"API Error (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2 # Exponential backoff
            else:
                print("API call failed after multiple retries.")
                return None # Indicate failure

def stitch_results(processed_chunks, overlap_lines):
    """Combines processed chunks, attempting to handle overlap."""
    if not processed_chunks:
        return ""

    final_transcript = processed_chunks[0]

    # Very basic overlap handling: Append chunks, assuming the AI mostly preserves
    # the start/end structure. Might need manual review at join points.
    # A more robust method would involve finding the last few lines of chunk N
    # and removing them from the start of chunk N+1 before appending, but this
    # is complex if the AI rephrased content.
    for i in range(1, len(processed_chunks)):
        # Simple newline join. Review the output file at chunk boundaries.
        final_transcript += "\n" + processed_chunks[i]

    # Simple post-processing: remove potential duplicate blank lines
    final_transcript = re.sub(r'\n\s*\n', '\n\n', final_transcript)

    return final_transcript


# --- Main Execution ---
if __name__ == "__main__":
    video_id = get_video_id(VIDEO_URL)
    if not video_id:
        exit(1)

    base_youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    raw_transcript = fetch_transcript(video_id)
    if not raw_transcript:
        exit(1)

    formatted_transcript = format_raw_transcript(raw_transcript)
    if not formatted_transcript:
        print("🛑 Error: Formatted transcript is empty.")
        exit(1)

    # print("\n--- Full Formatted Transcript (for debugging chunking) ---")
    # print(formatted_transcript[:1000] + "...") # Print start for verification
    # print("-----------------------------------------------------------\n")


    transcript_chunks = chunk_transcript(formatted_transcript, LINES_PER_CHUNK, OVERLAP_LINES)
    if not transcript_chunks:
        print("🛑 Error: No chunks were created.")
        exit(1)

    processed_results = []
    total_chunks = len(transcript_chunks)

    print(f"\nProcessing {total_chunks} chunks using {MODEL_NAME}...")
    for i, chunk in enumerate(transcript_chunks):
        print(f"--- Processing Chunk {i + 1}/{total_chunks} ---")
        # Small delay between API calls to avoid rate limits
        if i > 0:
            time.sleep(2) # Adjust delay as needed

        result = call_gemini_api(chunk, base_youtube_url)

        if result is not None:
            processed_results.append(result)
            print(f"Chunk {i + 1} processed successfully.")
        else:
            print(f"🛑 Error: Failed to process chunk {i + 1}. Skipping.")
            # Optional: Decide whether to stop or continue if a chunk fails
            # exit(1) # Uncomment to stop on first failure

    print("\n--- Stitching Results ---")
    # Note: Overlap handling here is basic. Review joins in the output file.
    final_output = stitch_results(processed_results, OVERLAP_LINES)


    print(f"\n--- Saving Final Transcript to {OUTPUT_FILENAME} ---")
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(final_output)
        print("✅ Successfully saved filtered transcript.")
    except IOError as e:
        print(f"🛑 Error saving file: {e}")

    print("\n✨ Process complete.")