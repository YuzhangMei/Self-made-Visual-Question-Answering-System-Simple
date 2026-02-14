import { useState, useEffect, useRef } from "react";

function App() {
  const [imageFile, setImageFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("onepass");
  const [result, setResult] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);

  const optionRefs = useRef([]);
  const recognitionRef = useRef(null);

  // ==========================
  // 🎙 Speech-to-Text
  // ==========================

  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setListening(true);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuestion(transcript);
    };

    recognition.start();
    recognitionRef.current = recognition;
  }

  // ==========================
  // 🔊 Text-to-Speech
  // ==========================

  function speak(text) {
    if (!window.speechSynthesis) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.lang = "en-US";

    window.speechSynthesis.speak(utterance);
  }

  // 当有新答案时自动朗读
  useEffect(() => {
    if (result) {
      speak(result);
    }
  }, [result]);

  // ==========================
  // Submit
  // ==========================

  async function handleSubmit(e) {
    e.preventDefault();

    if (!imageFile || !question.trim()) {
      alert("Please upload image and question.");
      return;
    }

    setLoading(true);
    setResult(null);
    setClarification(null);

    const formData = new FormData();
    formData.append("image", imageFile);
    formData.append("question", question);
    formData.append("mode", mode);

    const res = await fetch("http://localhost:5000/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setLoading(false);

    if (mode === "clarify" && data.clarification) {
      setClarification(data.clarification);
      setSessionId(data.session_id);
      speak(data.clarification.question);
    } else {
      setResult(data.answer);
    }
  }

  async function handleClarifySelection(option) {
    setLoading(true);

    const res = await fetch("http://localhost:5000/clarify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        selection: option,
      }),
    });

    const data = await res.json();
    setLoading(false);

    setClarification(null);
    setResult(data.answer);
  }

  // Focus first clarify option
  useEffect(() => {
    if (clarification && optionRefs.current[0]) {
      optionRefs.current[0].focus();
    }
  }, [clarification]);

  return (
    <div style={{ padding: 40, maxWidth: 800 }}>
      <h1>Ambiguity-Aware VQA (Voice Enabled)</h1>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setImageFile(e.target.files[0])}
          aria-label="Upload image"
        />
        <br /><br />

        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question..."
          style={{ width: "100%", padding: 8 }}
          aria-label="Question input"
        />

        <button
          type="button"
          onClick={startListening}
          style={{ marginLeft: 10 }}
          aria-label="Start voice input"
        >
          🎙 {listening ? "Listening..." : "Speak"}
        </button>

        <br /><br />

        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="onepass">One-pass</option>
          <option value="clarify">Clarify</option>
        </select>

        <button type="submit" style={{ marginLeft: 10 }}>
          {loading ? "Processing..." : "Submit"}
        </button>
      </form>

      {/* Clarification */}
      {clarification && (
        <div style={{ marginTop: 20 }}>
          <h3>{clarification.question}</h3>

          {clarification.options.map((option, index) => (
            <button
              key={index}
              ref={(el) => (optionRefs.current[index] = el)}
              onClick={() => handleClarifySelection(option)}
              style={{
                display: "block",
                margin: "10px 0",
                padding: "10px",
              }}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      {/* Final Answer */}
      {result && (
        <div style={{ marginTop: 20 }}>
          <h2>Answer:</h2>
          <p>{result}</p>
        </div>
      )}
    </div>
  );
}

export default App;
