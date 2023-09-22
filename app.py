import os 
import tempfile
import openai

import streamlit as st
import threading

from pytube import YouTube, Search
from urllib.parse import urlparse, parse_qs
from moviepy.editor import *

import time

from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx

from langchain.llms import OpenAI

openai.api_key = st.secrets["OPENAI_API_KEY"]

grid = []

NUM_OF_RELEVANT_REVIEWS = 5

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

def generate_transcript(video_id):
    transcript_text = "Sorry. Could not transcribe. Some error occured"
    with st.status("Downloading the review...") as status:
        with tempfile.TemporaryDirectory() as temp_dir:
            
            # Download video audio
            yt = YouTube(get_youtube_url(video_id))

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

def order_youtube_results_in_relevance(search_results):
    youtube_videos = {}
    input_to_gpt = "Following are the youtube video ids, titles and the number of views received for a movie review. Reply the video ids in the order of relevance based on whether the title relates to review or indicates some other content inside the youtube video. \n\n"
    for result in search_results:
        youtube_videos[result.video_id] = result
        input_to_gpt += "{\nId: " + result.video_id + ",\nTitle: " + result.title + ",\nViews: " + str(result.views) +"\n},\n" 

    input_to_gpt += "\nAnswer: "
    
    llm = OpenAI(openai_api_key=st.secrets["OPENAI_API_KEY"])
    response = llm.predict(input_to_gpt)
    response = response.replace("\n","")
    response = response.replace(" ","")
    response = response.replace(".","")
    response = response.split(",")

    relevant_yt_order = []
    for ytid in response:
        print(ytid)
        relevant_yt_order.append(youtube_videos[ytid])

    if (len(relevant_yt_order) < NUM_OF_RELEVANT_REVIEWS):
        return relevant_yt_order
    return relevant_yt_order[0:NUM_OF_RELEVANT_REVIEWS]

def search_relevant_yt_videos(search_query):
    youtube_search = Search(search_query)
    return order_youtube_results_in_relevance(youtube_search.results)

def get_youtube_url(video_id):
    return "https://www.youtube.com/watch?v=" + video_id

def get_transcript(video_id):
    if os.path.exists(f"{video_id}.txt"):
        # Load transcript from cache
        with open(f"{video_id}.txt", "r") as f:
            print("Transcript found in cache. Loading that for video id: ", video_id)
            transcript_text = f.read()
    else:
        # Generate transcript
        transcript_text = generate_transcript(video_id)
        with open(f"{video_id}.txt", "w") as f:
            f.write(transcript_text)
    
    return transcript_text

def process_video_per_container(container, youtube_video_object):
    col1, col2 = container.columns(2)

    transcript = get_transcript(youtube_video_object.video_id)
    
    with col1:
        st.video(get_youtube_url(youtube_video_object.video_id))
    
    with col2:
        st.write(transcript)

# Main application
def main(): 
    # Get Movie name from user
    st.title("Youtube Video Summary")
    movie_name = st.text_input("Movie Name:", placeholder="Jawan")

    if movie_name != "":
        relevant_yt_results = search_relevant_yt_videos(movie_name + " Movie Review")
        threads = []
        for index in range(len(relevant_yt_results)):
            result = relevant_yt_results[index]
            thread  = threading.Thread(target=process_video_per_container, args=(st.container(), result))
            ctx = get_script_run_ctx()
            add_script_run_ctx(thread)
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()


## execute main
if __name__ == "__main__":
    main()