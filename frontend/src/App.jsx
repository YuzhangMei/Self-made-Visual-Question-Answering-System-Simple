import { useState, useEffect, useRef } from "react";
import "./styles.css";

function App() {
  const [imageFile, setImageFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("clarify");
  const [result, setResult] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [focusReady, setFocusReady] = useState(false);
  const [followupText, setFollowupText] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);

  const recognitionRef = useRef(null);

  // ==========================
  // 🔊 Text-to-Speech
  // ==========================
  function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  }

  useEffect(() => {
    if (result) {
      speak(result);
    }
  }, [result]);

  useEffect(() => {
    if (clarification) {
      speak(clarification.question);
    }
  }, [clarification]);

  // ==========================
  // 🎙 Speech-to-Text
  // ==========================
  function startListening(targetSetter) {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition not supported.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      targetSetter(transcript);
    };

    recognition.start();
    recognitionRef.current = recognition;
  }

  // ==========================
  // Submit
  // ==========================
  async function handleSubmit(e) {
    e.preventDefault();

    const formData = new FormData();
    formData.append("image", imageFile);
    formData.append("question", question);
    formData.append("mode", mode);

    setLoading(true);

    const res = await fetch("http://localhost:5000/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setLoading(false);

    if (data.clarification) {
      setSessionId(data.session_id);
      setClarification(data.clarification);
      setResult(null);
      setFocusReady(false);
    } else {
      setResult(data.answer);
    }
  }

  async function handleClarifySelection(option) {
    const res = await fetch("http://localhost:5000/clarify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        selection: option,
      }),
    });

    const data = await res.json();
    setResult(data.answer);
    setClarification(null);
    setFocusReady(data.focus_ready);
  }

  async function handleFollowup() {
    if (!followupText.trim()) return;

    const res = await fetch("http://localhost:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        text: followupText,
      }),
    });

    const data = await res.json();
    setResult(data.answer);
    setFollowupText("");
  }

  async function handleEndSession() {
    await fetch("http://localhost:5000/end_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });

    setSessionId(null);
    setFocusReady(false);
    setClarification(null);
    setResult(null);
  }

  return (
    <div className="app-container">
      <h1 className="app-title">Multi-turn Ambiguity-Aware VQA</h1>
      <div className="input-group">
        <form onSubmit={handleSubmit}>
          <input
            type="file"
            accept="image/*,video/*"
            onChange={(e) => {
              setImageFile(e.target.files[0]);
              setSessionId(null);
              setFocusReady(false);
              setClarification(null);
            }}
          />
          <br /><br />

          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question"
            style={{ width: "80%" }}
          />

          <button
            type="button"
            onClick={() => startListening(setQuestion)}
            className="secondary"
          >
            🎙 {listening ? "Listening..." : "Speak"}
          </button>

          <br /><br />

          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="clarify">Clarify</option>
            <option value="onepass">One-pass</option>
          </select>

          <button type="submit" className="primary">
            {loading ? "Processing..." : "Submit"}
          </button>
        </form>
      </div>

      {clarification && (
        <div className="clarify-box">
          <h3>{clarification.question}</h3>
          {clarification.options.map((opt, idx) => (
            <button
              key={idx}
              onClick={() => handleClarifySelection(opt)}
              className="option-button"
            >
              {opt}
            </button>
          ))}
        </div>
      )}

      {result && (
        <div className="answer-box">
          <h2>Answer:</h2>
          <p>{result}</p>
        </div>
      )}

      {focusReady && (
        <div className="followup-box">
          <h3>Ask follow-up question</h3>
          <input
            type="text"
            value={followupText}
            onChange={(e) => setFollowupText(e.target.value)}
            style={{ width: "80%" }}
          />
          <button
            type="button"
            onClick={() => startListening(setFollowupText)}
            style={{ marginLeft: 10 }}
          >
            🎙 Speak
          </button>
          <br /><br />
          <button onClick={handleFollowup}>Send</button>
        </div>
      )}

      {sessionId && (
        <div className="end-session">
          <button
            onClick={handleEndSession}
            className="secondary"
          >
            End session / Start over
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
