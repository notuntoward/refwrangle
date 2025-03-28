"""Try to resegment youtube transcripts into redable, logical, single speaker chunks."""
# %%
import os
from openai import OpenAI
import instructor
from pydantic import BaseModel, Field
from youtube_transcript_api import YouTubeTranscriptApi
import re

# 1. Set up OpenAI client and patch with Instructor
client = instructor.from_openai(OpenAI())

# 2. Define the Pydantic model for segmented text
class Segment(BaseModel):
    start_ts: float = Field(
        ...,
        description="The start timestamp of the segment in seconds."
    )
    text: str = Field(
        ...,
        description="The exact text of the segment."
    )

# 3. Function to extract YouTube transcript
def get_youtube_transcript(video_id: str) -> list:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

# 4. Function to segment transcript using OpenAI
def segment_transcript(transcript: list, existing_segments=None):
    if not transcript:
        print("No transcript to process.")
        return [], "no_transcript"

    # Format transcript into a string that's easier for the model to understand
    formatted_transcript = "\n".join([f"ts={entry['start']:.2f} - {entry['text']}" for entry in transcript])

    # If continuing from a previous segment, prepend the existing text to the prompt
    if existing_segments:
        existing_text = "\n".join([f"[{s.start_ts:.2f}] {s.text}" for s in existing_segments])
        formatted_transcript = f"{existing_text}\n\nContinue from here:\n{formatted_transcript}"

    try:
        messages = [
                {"role": "system",
                 "content": """You are an expert in natural language processing and your task is to take a transcript of a video and re-segment it into coherent segments based on speaker turns and paragraph breaks.
                 Each segment should have a 'start_ts' (timestamp in seconds) and the corresponding 'text'. Retain the original language and be as accurate as possible.
                 Do not include content from multiple speakers into the same segment. Always ensure each speaker has their own segment.
                 Try to infer paragraph breaks where necessary, grouping sentences by speaker and topic.
                 Pay very close attention to timestamps: Use the timestamp that corresponds to the start of each speaker's segment.
                 If there is no speaker change, and the speaker continues with a new paragraph, you can create a new segment and use the timestamp that most closely aligns with the paragraph break.
                 The goal is to produce a transcript that is easy to read, with clear speaker separation and paragraph structure, without losing any of the original content."""},
                {"role": "user", "content": formatted_transcript},
            ]
        completion = client.chat.completions.create(
            model="gpt-4o",  # Experiment with different models
            messages=messages,
            max_tokens=15000, # Reduced max_tokens to allow room for the prompt
            response_model=list[Segment]
        )

        return completion, "success"

    except Exception as e:
        print(f"Error during segmentation: {e}")
        return [], "api_error"

# 5. Main function
def main(video_url: str):
    # Extract the video ID from the URL
    video_id = video_url.split("v=")[-1]

    # Get the transcript
    transcript = get_youtube_transcript(video_id)

    if transcript is None:
        print("Failed to retrieve transcript. Exiting.")
        return

    all_segments = []
    remaining_transcript = transcript

    while remaining_transcript:
        completion, finish_reason = segment_transcript(remaining_transcript, all_segments)

        if finish_reason == "success":
            segments = completion
            all_segments.extend(segments)

            print("Incomplete generation. Continuing...")
            # Find the approximate point in the transcript where the generation stopped.
            # Adapt this logic based on your specific needs and the structure of the transcript

            # Attempt to find where to continue based on the last segment generated.  Fragile!
            if segments:
                last_segment_text = segments[-1].text
                try:
                    last_segment_index = next(i for i, entry in enumerate(remaining_transcript) if last_segment_text in entry['text'])
                    remaining_transcript = remaining_transcript[last_segment_index+1:]
                except StopIteration:
                    print("Could not find where to continue.  Stopping")
                    break
            else:
                print("No segments returned, cannot continue.")
                break
        elif finish_reason == "stop":
            print("Finished generating the full transcript")
            break
        elif finish_reason == "api_error":
            print("API Error.  Stopping.")
            break
        elif finish_reason == "no_transcript":
            print("No Transcript. Stopping")
            break
        else:
            print(f"Stopped due to reason: {finish_reason}")
            break

    # Print the segmented transcript
    if all_segments:
        for segment in all_segments:
            print(f"[{segment.start_ts:.2f}] {segment.text}")
    else:
        print("No segments extracted.")

# Example usage
if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=Sx0J7dIlL7c"  # Replace with your YouTube video URL
    main(video_url)
