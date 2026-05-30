# 🤖 AI YouTube Video Analyzer

A premium, futuristic dark-themed Gradio web application that utilizes the Google Gemini API to analyze YouTube videos and extract rich, structured intelligence from transcripts instantly.

---

## 🌌 Features

The application provides a comprehensive analytical dashboard divided into highly styled tabs:

*   **📊 Dashboard**: High-level Executive Summary, actionable key takeaways, and a TL;DR / Simple Explanation (perfect for understanding complex ideas quickly).
*   **💡 Key Insights**: Interactive cards displaying core takeaways and contextual insights.
*   **📚 AI Learning Notes**: Structured conceptual guides, definitions, and tutorials extracted from the video topic.
*   **🎭 Sentiment & Tone**: Visual sentiment profiling, identifying delivery tone, and providing a detailed emotional arc analysis with color-coded status badges.
*   **⏱️ Timeline & Chapters**: A chronologically structured list of discussion topics with automatic timestamp references.
*   **📝 Subtitles Preview**: Full formatted transcripts with timestamp marks (`[MM:SS]`) and a direct **Download Subtitles** export button.

---

## 🛠️ Tech Stack

*   **Python 3.10+**
*   **Gradio** (Frontend UI framework)
*   **Google Generative AI SDK** (`google-generativeai`)
*   **YouTube Transcript API** (`youtube-transcript-api`)
*   **Python Dotenv** (`python-dotenv`)

---

## 📂 Project Structure

```directory
youtube-analyzer/
├── .env.example              # Environment variable template
├── .env                      # Secure configuration file (ignored by git)
├── README.md                 # Project documentation (this file)
├── walkthrough.md            # Execution and architecture details
└── youtube_video_analyzer.py # Main application single file source code
```

---

## 🚀 Setup & Execution

Follow these steps to run the application locally:

### 1. Install Dependencies
Install the required packages in your Python environment:
```bash
pip install gradio google-generativeai youtube-transcript-api python-dotenv typing-extensions
```

### 2. Configure Your API Key
1. Copy the `.env.example` file to create a `.env` file in the root of the project:
   ```bash
   cp .env.example .env
   ```
2. Open the newly created `.env` file and replace `YOUR_GEMINI_API_KEY` with your actual Google Gemini API key:
   ```env
   GEMINI_API_KEY=AIzaSyA123...your_key_here...
   ```
   *Note: If you do not have an API key, you can get one for free at [Google AI Studio](https://aistudio.google.com/).*

### 3. Run the App
Start the local server by executing:
```bash
python youtube_video_analyzer.py
```

Open your browser and navigate to the printed local URL:
👉 **[http://127.0.0.1:7860](http://127.0.0.1:7860)**

---

## ⚙️ Advanced Customization

Once the app is running, you can open the **Advanced Settings** accordion on the left sidebar to:
*   **Override API Key**: Change or paste a Gemini API Key directly in the UI without restarting the server.
*   **Select Processing Model**: Choose between `gemini-1.5-flash` (fast, efficient, recommended) and `gemini-1.5-pro` (deep, multi-step analytical reasoning).
