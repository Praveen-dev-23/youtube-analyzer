# Walkthrough: Futuristic AI YouTube Video Analyzer

We have successfully developed the **AI YouTube Video Analyzer** application! It is a complete, single-file Gradio web application with a premium dark glassmorphic design system, customized layout grid, timeline dashboards, and sentiment analysis profiles using the Gemini API.

## Changes Made

### 1. Main Application File
- **File Created**: [youtube_video_analyzer.py](file:///Users/praveen/IIT%20Class/youtube/youtube_video_analyzer.py)
- **Features Included**:
  - **URL Extractor**: Regex logic targeting standard, mobile, embedded, shortened, shorts, and live video links.
  - **YouTube oEmbed Client**: Fetches high-level metadata (title, author, high-res thumbnail) securely without heavy external binaries.
  - **Transcript Handler**: Pulls transcripts in English, fallback searching other languages, and performing auto-translations to English. It formats timestamps neatly (`[MM:SS]`) and supplies raw preview data.
  - **Gemini Structured Integration**: Leverages structured JSON schemas (`response_schema`) inside the Gemini 1.5 Flash SDK to ensure consistent, validated JSON outputs for TL;DRs, insights, timeline topics, sentiment tone, and learning notes.
  - **Premium Dark UI**: Formulated overrides for Gradio 6.0 CSS custom properties (glow gradients, neon accents, blur backdrops) and styled HTML cards to create a futuristic SaaS dashboard feel.
  - **Subtitles Exporter**: Supports downloading the parsed transcript as a local `.txt` file directly from the browser.

### 2. Environment Configuration
- **File Created**: [env.example](file:///Users/praveen/IIT%20Class/youtube/.env.example)
  - Acts as a template for user configuration.

---

## Setting Up and Running the Application

### Step 1: Install Dependencies
Ensure you are inside the project directory and run the following command in your terminal:
```bash
pip install gradio google-generativeai youtube-transcript-api python-dotenv typing-extensions
```

### Step 2: Configure Environment
1. Copy the template `.env.example` to `.env` in the root of the project:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` in a text editor and replace the placeholder value with your actual Gemini API key:
   ```env
   GEMINI_API_KEY=AIzaSy...your_gemini_api_key...
   ```
   > [!TIP]
   > Alternatively, you can also paste your Gemini API Key directly in the UI under **⚙️ Advanced Settings** once the app is running!

### Step 3: Run the Application
Start the local server by running:
```bash
python youtube_video_analyzer.py
```
After launching, open your browser and navigate to the local URL (usually `http://127.0.0.1:7860`).

---

## Verification & Testing Details
- Tested URL regex parameters with `dQw4w9WgXcQ` (Rick Astley - Never Gonna Give You Up) watch format, shortened format, and shorts format; all matched successfully.
- Handled Gradio 6.0 warnings regarding constructor deprecations (moved `css` and `theme` arguments to `.launch()`).
- Fixed parameter errors in layout blocks (removed invalid `style` keywords from `gr.Column` constructors and styled using custom classes in `CUSTOM_CSS`).
