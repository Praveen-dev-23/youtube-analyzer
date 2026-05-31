#!/usr/bin/env python3
"""
Futuristic AI YouTube Video Analyzer
====================================
An elegant, premium Gradio-based web application that analyzes YouTube videos
using the Gemini API and transcripts.

Setup Instructions:
-------------------
1. Install dependencies:
   pip install gradio google-generativeai youtube-transcript-api python-dotenv typing-extensions

2. Create a '.env' file in the same directory:
   GEMINI_API_KEY=YOUR_ACTUAL_API_KEY

3. Run the application:
   python youtube_video_analyzer.py
"""

import os
import re
import json
import urllib.request
from typing import Tuple, Dict, Any, List
from typing_extensions import TypedDict
from dotenv import load_dotenv
import gradio as gr
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables from .env file
load_dotenv()

# --- TYPE DEFINITIONS FOR STRUCTURED GEMINI OUTPUT ---
class Insight(TypedDict):
    title: str
    description: str

class Topic(TypedDict):
    topic: str
    explanation: str
    timestamp: str

class Sentiment(TypedDict):
    label: str
    tone: str
    explanation: str

class AnalysisResult(TypedDict):
    summary: str
    simple_explanation: str
    takeaways: List[str]
    insights: List[Insight]
    topics: List[Topic]
    sentiment: Sentiment
    learning_notes: List[str]

# --- UTILITIES ---

def extract_video_id(url: str) -> str:
    """
    Extracts the 11-character YouTube video ID from various URL formats.
    """
    if not url:
        raise ValueError("URL cannot be empty.")
    
    # Clean the input URL
    url = url.strip()
    
    # Various regex patterns for YouTube URLs
    patterns = [
        r'(?:https?:\/\/)?(?:www\.|m\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.|m\.)?youtube\.com\/watch\?.+&v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    # Try backup match for raw 11-char ID
    if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
        
    raise ValueError("Invalid YouTube URL format. Please paste a standard watch, mobile, shorts, or embed link.")

def fetch_video_metadata(video_id: str) -> Dict[str, Any]:
    """
    Fetches video metadata (title, author, thumbnail) using the YouTube oEmbed API.
    """
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        req = urllib.request.Request(
            oembed_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return {
                "title": data.get("title", f"YouTube Video ({video_id})"),
                "author": data.get("author_name", "Unknown Channel"),
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                "success": True
            }
    except Exception:
        # Fallback values if metadata fetch fails
        return {
            "title": f"YouTube Video ({video_id})",
            "author": "YouTube Content Creator",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "success": False
        }

def fetch_transcript(video_id: str) -> Tuple[str, str]:
    """
    Fetches the transcript using youtube-transcript-api.
    Returns: (formatted_transcript_with_timestamps, plain_text_transcript)
    """
    try:
        # List all transcripts to evaluate languages
        transcript_list = YouTubeTranscriptApi().list(video_id)
        
        # Try to find English first (either manual or generated)
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # Fallback to translate whatever is available into English
            available_transcripts = list(transcript_list._manually_created_transcripts.values()) + list(transcript_list._generated_transcripts.values())
            if not available_transcripts:
                raise RuntimeError("No captions or transcripts were found for this video.")
            transcript = available_transcripts[0].translate('en')
            
        entries = transcript.fetch()
        
        formatted_lines = []
        plain_words = []
        
        for entry in entries:
            if isinstance(entry, dict):
                start_time = entry.get('start', 0.0)
                text = entry.get('text', '')
            else:
                start_time = getattr(entry, 'start', 0.0)
                text = getattr(entry, 'text', '')
            
            # Formatting timestamp
            hours = int(start_time // 3600)
            minutes = int((start_time % 3600) // 60)
            seconds = int(start_time % 60)
            
            if hours > 0:
                time_str = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
            else:
                time_str = f"[{minutes:02d}:{seconds:02d}]"
                
            formatted_lines.append(f"{time_str} {text}")
            plain_words.append(text)
            
        return "\n".join(formatted_lines), " ".join(plain_words)
    except Exception as e:
        error_msg = str(e)
        if "Subtitles are disabled" in error_msg or "TranscriptsDisabled" in error_msg:
            raise RuntimeError("Transcripts are disabled or unavailable for this video. Please try a video that has subtitles.")
        elif "VideoUnavailable" in error_msg:
            raise RuntimeError("The video is unavailable, private, or restricted.")
        else:
            raise RuntimeError(f"Could not retrieve transcripts: {error_msg}")

# --- HTML TEMPLATES FOR PREMIUM DESIGN ---

def get_placeholder_html(title: str) -> str:
    """
    Placeholder state shown in tabs before analysis.
    """
    return f"""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border: 1px dashed rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 4rem 2rem;
        background: rgba(255, 255, 255, 0.01);
        color: #64748b;
        text-align: center;
        height: 100%;
        min-height: 320px;
    ">
        <div style="font-size: 2.5rem; margin-bottom: 1rem; filter: opacity(0.65);">🤖</div>
        <div style="font-weight: 600; font-size: 1.1rem; color: #94a3b8; margin-bottom: 0.25rem;">{title} Pending</div>
        <div style="font-size: 0.9rem; max-width: 320px;">Analyze a YouTube video on the left, and the structured intelligence details will compile here.</div>
    </div>
    """

def get_sentiment_styles(label: str) -> Tuple[str, str]:
    """
    Returns custom theme colors for sentiment badge styling.
    """
    l = label.lower()
    if any(w in l for w in ['positive', 'happy', 'optimistic', 'energetic', 'excited', 'inspirational']):
        return "rgba(16, 185, 129, 0.15)", "#10b981" # Green
    elif any(w in l for w in ['negative', 'critical', 'angry', 'sad', 'skeptical', 'warning', 'somber']):
        return "rgba(239, 68, 68, 0.15)", "#ef4444" # Red
    elif any(w in l for w in ['neutral', 'balanced', 'objective', 'calm']):
        return "rgba(100, 116, 139, 0.15)", "#94a3b8" # Slate
    else:
        return "rgba(59, 130, 246, 0.15)", "#3b82f6" # Blue/Educational

def generate_results_html(metadata: Dict[str, Any], data: AnalysisResult) -> Tuple[str, str, str, str]:
    """
    Converts structured JSON analysis data into beautiful HTML modules.
    Returns: (dashboard_html, insights_html, learning_notes_html, sentiment_html)
    """
    # 1. Dashboard (Summary, TL;DR, and Takeaways)
    takeaways_li = "".join([f"<li style='margin-bottom: 0.5rem;'>{item}</li>" for item in data.get('takeaways', [])])
    dashboard_html = f"""
    <div style="display: flex; flex-direction: column; gap: 1.5rem; animation: fadeIn 0.4s ease;">
        <!-- TL;DR Block -->
        <div style="
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.08) 0%, rgba(79, 172, 254, 0.08) 100%);
            border-left: 4px solid #00f2fe;
            padding: 1.25rem;
            border-radius: 8px;
        ">
            <h4 style="color: #00f2fe; font-weight: 700; margin: 0 0 0.5rem 0; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px;">💡 Simple Explanation (TL;DR)</h4>
            <p style="color: #e2e8f0; font-size: 1rem; line-height: 1.5; margin: 0;">{data.get('simple_explanation', '')}</p>
        </div>
        
        <!-- Detailed Summary -->
        <div>
            <h3 style="color: #ffffff; font-weight: 700; font-size: 1.25rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                <svg style="width: 20px; height: 20px; fill: #4facfe;" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
                Executive Summary
            </h3>
            <p style="color: #cbd5e1; font-size: 0.98rem; line-height: 1.6; margin: 0;">{data.get('summary', '')}</p>
        </div>
        
        <!-- Actionable Takeaways -->
        <div style="border-top: 1px solid rgba(255,255,255,0.06); padding-top: 1.25rem;">
            <h3 style="color: #ffffff; font-weight: 700; font-size: 1.25rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                <svg style="width: 20px; height: 20px; fill: #9b51e0;" viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>
                Key Takeaways
            </h3>
            <ul style="color: #cbd5e1; font-size: 0.98rem; line-height: 1.6; margin: 0; padding-left: 1.25rem;">
                {takeaways_li}
            </ul>
        </div>
    </div>
    """

    # 2. Insights & Topics
    insight_cards_html = ""
    for ins in data.get('insights', []):
        insight_cards_html += f"""
        <div style="
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-left: 4px solid #4facfe;
            border-radius: 8px;
            padding: 1.25rem;
            transition: all 0.3s ease;
        ">
            <h4 style="color: #00f2fe; font-weight: 700; font-size: 1.05rem; margin: 0 0 0.5rem 0;">💡 {ins.get('title', '')}</h4>
            <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; margin: 0;">{ins.get('description', '')}</p>
        </div>
        """
        
    topic_rows_html = ""
    for top in data.get('topics', []):
        t_badge = top.get('timestamp', '')
        if t_badge:
            badge_html = f'<span style="padding: 0.25rem 0.6rem; background: rgba(0, 242, 254, 0.15); color: #00f2fe; font-family: monospace; font-size: 0.8rem; font-weight: 700; border-radius: 4px; white-space: nowrap;">⏱️ {t_badge}</span>'
        else:
            badge_html = '<span style="padding: 0.25rem 0.6rem; background: rgba(255, 255, 255, 0.08); color: #94a3b8; font-family: monospace; font-size: 0.8rem; font-weight: 700; border-radius: 4px; white-space: nowrap;">📖 Topic</span>'
            
        topic_rows_html += f"""
        <div style="
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 1rem;
        ">
            {badge_html}
            <div style="flex: 1;">
                <h5 style="color: #ffffff; font-weight: 600; font-size: 0.98rem; margin: 0 0 0.25rem 0;">{top.get('topic', '')}</h5>
                <p style="color: #cbd5e1; font-size: 0.92rem; line-height: 1.5; margin: 0;">{top.get('explanation', '')}</p>
            </div>
        </div>
        """
        
    insights_html = f"""
    <div style="display: flex; flex-direction: column; gap: 1.5rem; animation: fadeIn 0.4s ease;">
        <div>
            <h3 style="color: #ffffff; font-weight: 700; font-size: 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                <svg style="width: 20px; height: 20px; fill: #4facfe;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H7c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.04-.42 1.99-1.07 2.75z"/></svg>
                Core Insights
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                {insight_cards_html or '<p style="color: #94a3b8;">No insights generated.</p>'}
            </div>
        </div>
        
        <div style="border-top: 1px solid rgba(255,255,255,0.06); padding-top: 1.25rem;">
            <h3 style="color: #ffffff; font-weight: 700; font-size: 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                <svg style="width: 20px; height: 20px; fill: #9b51e0;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.53c-.26-.81-1-1.4-1.9-1.4h-1v-3c0-.55-.45-1-1-1h-6v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
                Timeline & Discussion Topics
            </h3>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                {topic_rows_html or '<p style="color: #94a3b8;">No discussion topics extracted.</p>'}
            </div>
        </div>
    </div>
    """

    # 3. Learning Notes
    notes_list_html = ""
    for note in data.get('learning_notes', []):
        notes_list_html += f"""
        <div style="
            background: rgba(155, 81, 224, 0.04);
            border: 1px solid rgba(155, 81, 224, 0.12);
            border-radius: 8px;
            padding: 1.25rem;
            display: flex;
            gap: 1rem;
            align-items: flex-start;
        ">
            <span style="font-size: 1.25rem; line-height: 1;">📘</span>
            <div style="color: #cbd5e1; font-size: 0.98rem; line-height: 1.6; flex: 1;">{note}</div>
        </div>
        """
    learning_notes_html = f"""
    <div style="display: flex; flex-direction: column; gap: 1.25rem; animation: fadeIn 0.4s ease;">
        <h3 style="color: #ffffff; font-weight: 700; font-size: 1.25rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
            <svg style="width: 20px; height: 20px; fill: #4facfe;" viewBox="0 0 24 24"><path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3zm0 13c-3.72 0-7.01-1.63-8-4.22L12 16l8-4.22c-.99 2.59-4.28 4.22-8 4.22z"/></svg>
            AI Learning Notes
        </h3>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            {notes_list_html or '<p style="color: #94a3b8;">No learning notes generated.</p>'}
        </div>
    </div>
    """

    # 4. Sentiment & Tone
    sentiment_data = data.get('sentiment', {})
    s_label = sentiment_data.get('label', 'Neutral')
    s_tone = sentiment_data.get('tone', 'Informative')
    s_explanation = sentiment_data.get('explanation', '')
    
    bg_color, text_color = get_sentiment_styles(s_label)
    
    sentiment_html = f"""
    <div style="display: flex; flex-direction: column; gap: 1.5rem; animation: fadeIn 0.4s ease;">
        <h3 style="color: #ffffff; font-weight: 700; font-size: 1.25rem; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.5rem;">
            <svg style="width: 20px; height: 20px; fill: #9b51e0;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            Sentiment & Tone Profile
        </h3>
        
        <div style="
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 1.5rem;
        ">
            <!-- Sentiment Score Gauge -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="font-size: 1rem; font-weight: 700; color: #ffffff;">Primary Class</span>
                <span style="
                    font-size: 0.85rem; 
                    font-weight: 700; 
                    padding: 0.3rem 0.75rem; 
                    background: {bg_color}; 
                    color: {text_color}; 
                    border-radius: 20px; 
                    text-transform: uppercase; 
                    letter-spacing: 0.5px;
                ">
                    {s_label}
                </span>
            </div>
            
            <!-- Custom Progress Bar representation -->
            <div style="width: 100%; height: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; overflow: hidden; margin-bottom: 1.25rem;">
                <div style="height: 100%; width: 100%; background: linear-gradient(90deg, #00f2fe 0%, #4facfe 50%, #9b51e0 100%); border-radius: 4px;"></div>
            </div>
            
            <div style="margin-bottom: 1.25rem;">
                <h4 style="color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; margin: 0 0 0.25rem 0; letter-spacing: 0.5px;">Emotional Tone & Delivery</h4>
                <p style="color: #e2e8f0; font-size: 1.05rem; font-weight: 500; margin: 0;">🔊 {s_tone}</p>
            </div>
            
            <div>
                <h4 style="color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; margin: 0 0 0.25rem 0; letter-spacing: 0.5px;">Detailed Tone Analysis</h4>
                <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6; margin: 0;">{s_explanation}</p>
            </div>
        </div>
    </div>
    """

    return dashboard_html, insights_html, learning_notes_html, sentiment_html

# --- GENAI LOGIC ---

def run_analysis(url: str, custom_api_key: str, model_name: str) -> Tuple[str, gr.DownloadButton, str, str, str, str, str, str]:
    """
    Main controller for analyzing a YouTube link.
    """
    # 1. Resolve API Key
    api_key = custom_api_key.strip() if custom_api_key else os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return (
            "<div class='glass-container' style='border-color: #ef4444 !important; color: #ef4444;'>⚠️ Error: Gemini API key is missing. Please set the GEMINI_API_KEY environment variable or paste it in the API settings.</div>",
            None,
            get_placeholder_html("Dashboard"),
            get_placeholder_html("Insights"),
            get_placeholder_html("Learning Notes"),
            get_placeholder_html("Sentiment Analysis"),
            "",
            "Please configure your Gemini API Key."
        )
        
    try:
        # 2. Extract Video ID
        video_id = extract_video_id(url)
    except Exception as e:
        return (
            f"<div class='glass-container' style='border-color: #ef4444 !important; color: #ef4444;'>⚠️ Error: {str(e)}</div>",
            None,
            get_placeholder_html("Dashboard"),
            get_placeholder_html("Insights"),
            get_placeholder_html("Learning Notes"),
            get_placeholder_html("Sentiment Analysis"),
            "",
            "Invalid YouTube URL."
        )
        
    # 3. Fetch Metadata and Transcripts
    metadata = fetch_video_metadata(video_id)
    
    try:
        formatted_transcript, raw_transcript = fetch_transcript(video_id)
    except Exception as e:
        # Setup error display
        return (
            f"""
            <div style="border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; background: rgba(239, 68, 68, 0.05); overflow: hidden;">
                <img src="{metadata['thumbnail']}" style="width: 100%; aspect-ratio: 16/9; object-fit: cover; filter: grayscale(80%);" alt="Thumbnail">
                <div style="padding: 1.25rem;">
                    <h3 style="color: #ffffff; font-size: 1.1rem; font-weight: 700; margin: 0 0 0.5rem 0;">{metadata['title']}</h3>
                    <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 1rem;">📺 {metadata['author']}</p>
                    <div style="color: #ef4444; font-size: 0.9rem; font-weight: 600; padding: 0.75rem; background: rgba(239, 68, 68, 0.1); border-radius: 6px; border: 1px solid rgba(239, 68, 68, 0.2);">
                        ❌ {str(e)}
                    </div>
                </div>
            </div>
            """,
            None,
            get_placeholder_html("Dashboard"),
            get_placeholder_html("Insights"),
            get_placeholder_html("Learning Notes"),
            get_placeholder_html("Sentiment Analysis"),
            "",
            f"Transcript fetching failed: {str(e)}"
        )

    # 4. Configure Gemini Client
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=(
                "You are a state-of-the-art AI YouTube Video Analyst. Your task is to analyze "
                "the provided video transcript and generate a structured analytical result. "
                "Explain the concepts clearly, summarize accurately, extract useful insights, "
                "detect the emotional sentiment/tone of the speaker, generate concise bullet points, "
                "simplify complex ideas, and highlight key discussion topics (with approximate timestamps if they are referenced or implied by the sequence)."
            )
        )
        
        prompt = f"""
        Analyze the following YouTube video transcript.
        
        Video Title: {metadata['title']}
        Channel Name: {metadata['author']}
        
        Transcript text:
        {raw_transcript[:50000]}  # Clip to keep inside token windows safely
        
        Please return a strictly formatted JSON response mapping the following JSON schema:
        {{
          "summary": "Provide a comprehensive, high-level overview of the video's contents (1-2 paragraph). Ensure it is extremely informative.",
          "simple_explanation": "Provide a simple, jargon-free explanation as if explaining it to a 10-year-old child.",
          "takeaways": [
            "Actionable lesson / takeaway 1",
            "Actionable lesson / takeaway 2",
            "Actionable lesson / takeaway 3"
          ],
          "insights": [
            {{
              "title": "A punchy title for this insight",
              "description": "Elaborate in detail on the insight, explaining what was revealed, why it matters, and the context."
            }}
          ],
          "topics": [
            {{
              "topic": "Name of the main topic or segment",
              "explanation": "Summarize what was discussed in this section of the video.",
              "timestamp": "Provide a MM:SS timestamp where this topic is discussed. Infer this from the context or leave blank."
            }}
          ],
          "sentiment": {{
            "label": "The overall sentiment class (e.g. Positive, Informative, Critical, Urgent, Humorous, Analytical)",
            "tone": "Describe the emotional delivery, energy levels, and tone of the speaker.",
            "explanation": "Provide a detailed analytical explanation of why the sentiment and tone are classified this way."
          }},
          "learning_notes": [
            "A structured learning note explaining a core definition, formula, method, or technical concept mentioned in the video.",
            "Another educational tutorial summary bullet point..."
          ]
        }}
        """
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResult
            )
        )
        
        # Parse output
        analysis_data = json.loads(response.text)
        
    except Exception as e:
        return (
            f"""
            <div style="border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; background: rgba(20, 16, 42, 0.5); overflow: hidden;">
                <img src="{metadata['thumbnail']}" style="width: 100%; aspect-ratio: 16/9; object-fit: cover;" alt="Thumbnail">
                <div style="padding: 1.25rem;">
                    <h3 style="color: #ffffff; font-size: 1.1rem; font-weight: 700; margin: 0 0 0.5rem 0;">{metadata['title']}</h3>
                    <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 1rem;">📺 {metadata['author']}</p>
                    <div style="color: #ef4444; font-size: 0.9rem; font-weight: 600; padding: 0.75rem; background: rgba(239, 68, 68, 0.1); border-radius: 6px; border: 1px solid rgba(239, 68, 68, 0.2);">
                        ❌ Gemini Generation Error: {str(e)}
                    </div>
                </div>
            </div>
            """,
            None,
            get_placeholder_html("Dashboard"),
            get_placeholder_html("Insights"),
            get_placeholder_html("Learning Notes"),
            get_placeholder_html("Sentiment Analysis"),
            formatted_transcript,
            f"Gemini API Error: {str(e)}"
        )

    # 5. Populate successful results
    video_card_html = f"""
    <div style="
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        background: rgba(20, 16, 42, 0.55);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        overflow: hidden;
        animation: fadeIn 0.4s ease;
    ">
        <div style="position: relative; overflow: hidden; aspect-ratio: 16/9;">
            <img src="{metadata['thumbnail']}" style="width: 100%; height: 100%; object-fit: cover;" alt="Thumbnail">
            <div style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.75); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-family: monospace;">HD</div>
        </div>
        <div style="padding: 1.25rem;">
            <span style="display: inline-block; padding: 0.25rem 0.6rem; background: rgba(0, 242, 254, 0.15); color: #00f2fe; font-size: 0.7rem; font-weight: 700; border-radius: 4px; text-transform: uppercase; margin-bottom: 0.75rem; letter-spacing: 0.5px;">Analyzed</span>
            <h3 style="color: #ffffff; font-size: 1.1rem; font-weight: 700; line-height: 1.4; margin: 0 0 0.5rem 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">{metadata['title']}</h3>
            <p style="color: #94a3b8; font-size: 0.88rem; margin: 0; font-weight: 500;">📺 {metadata['author']}</p>
        </div>
    </div>
    """
    
    # Save transcript to temp file to support downloading
    temp_transcript_path = "/tmp/transcript.txt"
    try:
        with open(temp_transcript_path, "w") as f:
            f.write(formatted_transcript)
        download_btn_update = gr.update(value=temp_transcript_path, visible=True)
    except Exception:
        download_btn_update = gr.update(visible=False)

    dash_html, ins_html, learn_html, sent_html = generate_results_html(metadata, analysis_data)
    
    return (
        video_card_html,
        download_btn_update,
        dash_html,
        ins_html,
        learn_html,
        sent_html,
        formatted_transcript,
        "Success! Analysis completed."
    )


# --- PREMIUM GRAPHIC THEME CSS ---
CUSTOM_CSS = """
/* Imports & Custom Theme Variables */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root, .dark {
    --body-background-fill: radial-gradient(circle at 50% 50%, #0c0822 0%, #03000b 100%) !important;
    --background-fill-primary: rgba(18, 12, 38, 0.45) !important;
    --background-fill-secondary: rgba(10, 8, 20, 0.7) !important;
    --border-color-primary: rgba(255, 255, 255, 0.08) !important;
    --border-color-accent: #00f2fe !important;
    --input-background-fill: rgba(8, 5, 20, 0.6) !important;
    --input-border-color: rgba(255, 255, 255, 0.1) !important;
    --input-border-color-focus: #00f2fe !important;
    --button-primary-background-fill: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
    --button-primary-background-fill-hover: linear-gradient(135deg, #4facfe 0%, #9b51e0 100%) !important;
    --button-primary-text-color: #03001e !important;
    --text-color-primary: #f8fafc !important;
    --text-color-secondary: #94a3b8 !important;
    --radius-lg: 16px !important;
    --radius-md: 12px !important;
    --radius-sm: 8px !important;
}

body, .gradio-container {
    font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif !important;
}

/* Glassmorphism Panel Override */
.glass-container {
    background: rgba(18, 12, 38, 0.4) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.4) !important;
    padding: 1.5rem !important;
    transition: all 0.3s ease-in-out !important;
}

.glass-container:hover {
    border: 1px solid rgba(139, 92, 246, 0.25) !important;
    box-shadow: 0 15px 45px 0 rgba(139, 92, 246, 0.12) !important;
}

/* Hero elements */
.hero-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 3rem !important;
    font-weight: 800 !important;
    text-align: center !important;
    background: linear-gradient(135deg, #00f2fe 0%, #4facfe 40%, #9b51e0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    margin-bottom: 0.25rem !important;
    letter-spacing: -1px !important;
    filter: drop-shadow(0 2px 10px rgba(0, 242, 254, 0.15));
}

.hero-subtitle {
    font-size: 1.15rem !important;
    text-align: center !important;
    color: #94a3b8 !important;
    margin-bottom: 2rem !important;
    font-weight: 400 !important;
}

/* Animated glow buttons */
.analyze-btn {
    box-shadow: 0 4px 15px rgba(0, 242, 254, 0.25) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
}

.analyze-btn:hover {
    box-shadow: 0 6px 22px rgba(0, 242, 254, 0.45), 0 0 30px rgba(155, 81, 224, 0.3) !important;
    transform: translateY(-1px) scale(1.01);
}

.analyze-btn:active {
    transform: translateY(1px);
}

/* Custom Gradio Tab Adjustments */
.tab-nav {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.tab-nav button {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: #64748b !important;
    transition: all 0.3s ease !important;
    border-bottom: 2px solid transparent !important;
}

.tab-nav button.selected {
    color: #00f2fe !important;
    border-bottom-color: #00f2fe !important;
    background: transparent !important;
}

.tab-nav button:hover:not(.selected) {
    color: #e2e8f0 !important;
}

/* Scrollbar adjustment */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(10, 8, 20, 0.4);
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 242, 254, 0.35);
}

/* General Fade In Animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.margin-top-1 {
    margin-top: 1rem !important;
}
"""

# --- GRADIO BUILDER ---

with gr.Blocks() as app:
    
    # Hero Title Section
    gr.HTML("""
        <div style="margin-top: 1.5rem; margin-bottom: 1.5rem;">
            <h1 class="hero-title">AI YouTube Video Analyzer</h1>
            <p class="hero-subtitle">Analyze any YouTube video instantly using Gemini AI</p>
        </div>
    """)
    
    with gr.Row():
        
        # LEFT COLUMN (Control Panel)
        with gr.Column(scale=1):
            with gr.Column(elem_classes=["glass-container"]):
                gr.HTML("<h3 style='color: #ffffff; font-weight: 700; font-size: 1.15rem; margin-top:0; margin-bottom: 1rem;'>🔗 Source Video</h3>")
                
                url_input = gr.Textbox(
                    label="YouTube URL", 
                    placeholder="https://www.youtube.com/watch?v=...",
                    lines=1
                )
                
                analyze_btn = gr.Button("Analyze Video", variant="primary", elem_classes=["analyze-btn"])
                
                # API / Advanced settings
                with gr.Accordion("⚙️ Advanced Settings", open=False):
                    api_override = gr.Textbox(
                        value=os.getenv("GEMINI_API_KEY", ""),
                        label="Gemini API Key (Overrides .env)",
                        placeholder="AIzaSy...",
                        type="password"
                    )
                    model_dropdown = gr.Dropdown(
                        choices=["gemini-3.5-flash", "gemini-3.5-pro", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
                        value="gemini-3.5-flash",
                        label="AI Processing Model"
                    )
            
            # Video Metadata Card Panel
            with gr.Column(elem_classes=["glass-container", "margin-top-1"]):
                gr.HTML("<h3 style='color: #ffffff; font-weight: 700; font-size: 1.15rem; margin-top:0; margin-bottom: 1rem;'>🎥 Video Information</h3>")
                video_preview = gr.HTML(value=get_placeholder_html("Video Details"))
                download_transcript_btn = gr.DownloadButton(
                    label="📥 Download Subtitles", 
                    visible=False,
                    variant="secondary"
                )
                
            # Log / Status panel
            with gr.Column(elem_classes=["glass-container", "margin-top-1"]):
                status_box = gr.Textbox(
                    value="System Standby. Awaiting URL input...",
                    label="Application Status",
                    interactive=False
                )
                
        # RIGHT COLUMN (Analysis Results)
        with gr.Column(scale=2, elem_classes=["glass-container"]):
            with gr.Tabs(elem_classes=["tabs"]):
                
                with gr.TabItem("📊 Dashboard"):
                    dashboard_tab = gr.HTML(value=get_placeholder_html("Dashboard"))
                    
                with gr.TabItem("💡 Key Insights"):
                    insights_tab = gr.HTML(value=get_placeholder_html("Insights"))
                    
                with gr.TabItem("📚 Learning Notes"):
                    notes_tab = gr.HTML(value=get_placeholder_html("Learning Notes"))
                    
                with gr.TabItem("🎭 Sentiment & Tone"):
                    sentiment_tab = gr.HTML(value=get_placeholder_html("Sentiment Profile"))
                    
                with gr.TabItem("📝 Subtitles Preview"):
                    transcript_text_preview = gr.Textbox(
                        label="Subtitles & Transcripts (with approximate timestamps)", 
                        placeholder="Subtitles will load here...",
                        lines=15, 
                        max_lines=25, 
                        interactive=False
                    )

    # Wire up the execution event
    analyze_btn.click(
        fn=run_analysis,
        inputs=[url_input, api_override, model_dropdown],
        outputs=[
            video_preview, 
            download_transcript_btn, 
            dashboard_tab, 
            insights_tab, 
            notes_tab, 
            sentiment_tab, 
            transcript_text_preview, 
            status_box
        ],
        show_progress="full"
    )

if __name__ == "__main__":
    # Launch local server
    app.launch(share=False, css=CUSTOM_CSS, theme=gr.themes.Default())
