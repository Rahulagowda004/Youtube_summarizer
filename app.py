import os
import validators
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import UnstructuredURLLoader
from yt_dlp import YoutubeDL
from langchain.docstore.document import Document
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Streamlit APP
st.set_page_config(page_title="Youtube summarizer", page_icon="📺", layout="wide")
st.title("Youtube summarizer")
st.subheader("Summarize any youtube video in a few seconds")

# Get the Groq API Key and URL (YT or website) to be summarized
with st.sidebar:
    groq_api_key = st.text_input("Groq API Key", value="", type="password")

generic_url = st.text_input("URL", label_visibility="collapsed")

# Set Groq API key as environment variable
if groq_api_key.strip():
    os.environ["GROQ_API_KEY"] = groq_api_key
    llm = ChatGroq(model="Gemma-7b-It")
else:
    st.error("Please provide a valid Groq API Key")

prompt_template = """
Provide a summary of the following content in 300 words:
Content:{text}
"""
prompt = PromptTemplate(template=prompt_template, input_variables=["text"])

def get_transcript(video_id):
    """Retrieve the transcript of the video using youtube_transcript_api."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript])
        return transcript_text
    except (TranscriptsDisabled, NoTranscriptFound):
        return None

if st.button("Summarize the Content from YT or Website"):
    if not groq_api_key.strip() or not generic_url.strip():
        st.error("Please provide the information to get started")
    elif not validators.url(generic_url):
        st.error("Please enter a valid URL. It can be a YT video URL or website URL")
    else:
        try:
            with st.spinner("Waiting..."):
                docs = []
                if "youtube.com" in generic_url:
                    try:
                        # Extract video ID from URL
                        video_id = generic_url.split("v=")[-1].split("&")[0]
                        
                        # Attempt to get the transcript
                        transcript_text = get_transcript(video_id)
                        
                        if transcript_text:
                            # Use transcript as content if available
                            content = transcript_text
                        else:
                            # Fallback to title and description if no transcript
                            ydl_opts = {"quiet": True, "skip_download": True, "format": "bestaudio/best"}
                            with YoutubeDL(ydl_opts) as ydl:
                                info_dict = ydl.extract_info(generic_url, download=False)
                                title = info_dict.get("title", "No Title")
                                description = info_dict.get("description", "No Description")
                                content = f"{title}\n\n{description}"
                                
                        docs = [Document(page_content=content)]
                    except Exception as yt_exception:
                        st.warning(f"Unable to retrieve YouTube data: {yt_exception}")
                else:
                    loader = UnstructuredURLLoader(
                        urls=[generic_url],
                        ssl_verify=False,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    docs = [Document(page_content=doc['text']) for doc in loader.load()]

                if docs:
                    # Chain for summarization
                    chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt)
                    output_summary = chain.run(docs)
                    st.success(output_summary)
                else:
                    st.error("Failed to load content from the provided URL.")
        except Exception as e:
            st.error(f"Exception while processing the URL: {e}")
