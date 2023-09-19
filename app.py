import os 
import tempfile
import openai

import streamlit as st

from pytube import YouTube
from urllib.parse import urlparse, parse_qs
from moviepy.editor import *

openai.api_key = st.secrets["OPENAI_API_KEY"]

# Transcripe MP3 Audio function
def transscribe_audio(file_path):
    file_size = os.path.getsize(file_path)
    file_size_in_mb = file_size / (1024 * 1024)
    print("File size in MB: ", file_size_in_mb)

    if file_size_in_mb < 25:
        with open(file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript
    else:
        print("Please provide a smaller audio file (max 25mb).")

def get_transcript(url, video_id):
    transcript_text = "Sorry. Could not transcribe. Some error occured"
    with st.status("Downloading the review...") as status:
        with tempfile.TemporaryDirectory() as temp_dir:
            
            # Download video audio
            yt = YouTube(url)

            # Get the first available audio stream and download this stream
            audio_stream = yt.streams.filter(only_audio=True).first()
            audio_stream.download(output_path=temp_dir)

            status.update(label="Downloaded the review. Transcribing in progress ...")

            # Convert the audio file to MP3
            audio_path = os.path.join(temp_dir, audio_stream.default_filename)
            audio_clip = AudioFileClip(audio_path)
            audio_clip.write_audiofile(os.path.join(temp_dir, f"{video_id}.mp3"))

            # Keep the path of the audio file
            audio_path = f"{temp_dir}/{video_id}.mp3"

            # Transscripe the MP3 audio to text
            transcript = transscribe_audio(audio_path)
            transcript_text = transcript.text
            
            # Delete the original audio file
            os.remove(audio_path)

            status.update(label="Transcription complete ...", state="complete")
    
    return transcript_text

# Main application
def main(): 
    # Get YouTube video URL from user
    st.title("Youtube Video Summary")
    url = st.text_input("YouTube Video URL:", "https://www.youtube.com/watch?v=FakUF0bwbQM")
    st.video(url)
    
    # Extract the video ID from the url
    query = urlparse(url).query
    params = parse_qs(query)
    video_id = params["v"][0]

    if os.path.exists(f"{video_id}.txt"):
        # Load transcript from cache
        with open(f"{video_id}.txt", "r") as f:
            print("Transcript found in cache. Loading that for video id: ", video_id)
            transcript_text = f.read()
    else:
        # Generate transcript
        transcript_text = get_transcript(url, video_id)
        with open(f"{video_id}.txt", "w") as f:
            f.write(transcript_text)

    st.write(transcript_text)



## execute main
if __name__ == "__main__":
    main()