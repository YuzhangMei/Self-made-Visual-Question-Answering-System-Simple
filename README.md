# Clarivision  
**A human-centered Visual Question Answering System Prototype**

Author: Yuzhang (Leo) Mei  

---
## Overview
Clarivision is a multi-turn, ambiguity-aware Visual Question Answering (VQA) system designed to assist blind and low-vision (BLVI) users.

Unlike traditional one-pass VQA systems, Clarivision:

- Detects ambiguity in user questions  
- Engages in clarification dialogue  
- Supports both multi-turn interaction and one-pass response 
- Supports both image and short video input  
- Incorporates temporal reasoning across video frames  
- Provides voice input (Speech-to-Text) and voice output (Text-to-Speech)  
- Includes screen-reader-friendly UI elements  

This project was developed as part of the Human-AI Lab SURE Starter Task (Project #11).

---

## Features

### ✅ Multi-turn Clarification
If a question is ambiguous (e.g., multiple similar objects exist), the system asks follow-up clarification questions and provides buttons as feedback before answering.

### ✅ One-pass Structured Response for Ambiguity
Generates grouped and structured descriptions when ambiguity is present.

### ✅ Video Support
- Extracts key frames
- Aggregates objects across time
- Detects temporal ambiguity
- Allows time-aware clarification

### ✅ Accessibility Features
- Keyboard navigation
- Screen-reader-friendly labeling
- Text-to-Speech (automatic answer narration)
- Speech-to-Text input

---
## System Architecture
1. Frontend (React)
2. Flask Backend API
3. Vision Model (GPT-4V in this prototype, other models supported as well)
4. Ambiguity Detection
5. Session-based Multi-turn Dialogue

---
## Repository Structure

```text
Self-made-Visual-Question-Answering-System-Simple/
├── README.md
├── backend/
│   ├──ambiguity.py
│   ├──app.py
│   ├──llm_answer.py
│   ├──openai_vision.py
│   ├──requirements.txt
│   ├──response_generator.py
│   ├──session_store.py
│   ├──temporal_aggregator.py
│   ├──temporal_ambiguity.py
│   ├──video_processor.py
├── frontend/
│   ├──src/
│       ├──App.jsx
│       ├──styles.css
├── .vscode
│   ├── settings.json
├── .gitignore
```
*Notes: please neglect the files included in the repo but not listed in the tree :)*

---

## Setup Instructions

### Step 1: Clone the Repository
```bash
git clone https://github.com/YuzhangMei/Self-made-Visual-Question-Answering-System-Simple
cd <your-repo>
```
### Step 2-a: Create a Virtual Environment
```bash
cd backend
python -m venv venv
```
### Step 2-b: Activate the Virtual Environment
**macOS / Linux**
```bash
source venv/bin/activate
```
**Windows**
```bash
venv\Scripts\activate
```
### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
If no requirements.txt is provided, install manually:
```bash
pip install flask flask-cors openai
```
### Step 4: Set OpenAI API Key
Create an environment variable:
**macOS / Linux**
```bash
export OPENAI_API_KEY="your_api_key_here"
```
**Windows**
```bash
setx OPENAI_API_KEY "your_api_key_here"
```
Restart terminal after setting.
### Step 5: Run Backend Server
Run the following command in `backend/`.
```bash
python app.py
```
Backend runs at: http://localhost:5000 .

**The following steps serve for the frontend setup (React).**
### Step 6: Install Node Dependencies
```bash
cd frontend
npm install
```
### Step 7: Run Frontend
```bash
npm run dev
```
Frontend runs at: http://localhost:5173 .

---

## How to use
1. Upload an image or short video.
2. Enter a question either by typing or speaking.
3. Select mode:
    - Clarify (iterative clarification; multi-turn interaction)
    - One-pass (one-pass response; direct structured answer)
4. If ambiguity is detected, choose the correct object from the buttons given.
5. Continue with follow-up questions if desired.
6. Click "End Session" to reset.

---

## Design Highlights
### Ambiguity Detection

The system explicitly detects when:
- Multiple similar objects are present
- Temporal ambiguity exists in video
- The user's question underspecifies the referent

It then generates clarification options before answering.

### Temporal Reasoning
For video inputs:
- Frames are sampled
- Objects are detected per frame
- Objects are aggregated across timestamps
- Clarification options include time spans

### Accessibility
- Fully keyboard navigable
- Buttons are screen-reader compatible
- Automatic TTS narration
- Built-in Speech Recognition input

---

## Known Limitations
- Temporal spans are based on sampled frames, not continuous tracking.
- Object detection quality depends on the underlying vision model.
- No persistent database (sessions are in-memory).

## Future Improvements
- Real-time video stream support
- Object tracking instead of frame-based aggregation
- Improved semantic merging of similar object labels
- Persistent session storage

## License
This project is for academic research purposes.

## Acknowledgements
Developed for the Human-AI Lab SURE Starter Task.

Special thanks to the lab mentors (Prof. Anhong Guo and Rosiana Natalie) for their guidance.