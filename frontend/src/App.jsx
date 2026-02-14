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
  const [liveMessage, setLiveMessage] = useState("");

  const optionRefs = useRef([]);

  // ==========================
  // Speech-to-text
  // ==========================
  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition not supported.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setListening(true);
      setLiveMessage("Voice input started.");
    };

    recognition.onend = () => {
      setListening(false);
      setLiveMessage("Voice input stopped.");
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuestion(transcript);
      setLiveMessage("Question updated from voice input.");
    };

    recognition.start();
  }

  // ==========================
  // Text-to-speech
  // ==========================
  function speak(text) {
    if (!window.speechSynthesis) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    window.speechSynthesis.speak(utterance);
  }

  useEffect(() => {
    if (result) {
      speak(result);
      setLiveMessage("Answer generated and spoken.");
    }
  }, [result]);

  // ==========================
  // Submit
  // ==========================
  async function handleSubmit(e) {
    e.preventDefault();

    if (!imageFile || !question.trim()) {
      setLiveMessage("Please upload image and enter question.");
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
      setLiveMessage("Clarification required.");
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

  return (
    <div style={{ padding: 40, maxWidth: 800 }}>
      <h1>Accessible Ambiguity-Aware VQA</h1>

      <form onSubmit={handleSubmit}>

        <label htmlFor="imageUpload">Upload Image</label><br />
        <input
          id="imageUpload"
          type="file"
          accept="image/*"
          onChange={(e) => setImageFile(e.target.files[0])}
        />
        <br /><br />

        <label htmlFor="questionInput">Ask a Question</label><br />
        <input
          id="questionInput"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          style={{ width: "100%", padding: 8 }}
        />

        <button
          type="button"
          onClick={startListening}
          aria-pressed={listening}
          aria-label="Start voice input"
          style={{ marginLeft: 10 }}
        >
          {listening ? "Listening..." : "Speak"}
        </button>

        <br /><br />

        <fieldset>
          <legend>Select Mode</legend>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="onepass">One-pass</option>
            <option value="clarify">Clarify</option>
          </select>
        </fieldset>

        <button type="submit">
          {loading ? "Processing..." : "Submit"}
        </button>
      </form>

      {/* Clarification */}
      {clarification && (
        <div role="alert" aria-live="assertive" style={{ marginTop: 20 }}>
          <h2>{clarification.question}</h2>

          {clarification.options.map((option, index) => (
            <button
              key={index}
              onClick={() => handleClarifySelection(option)}
              style={{ display: "block", margin: "10px 0" }}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      {/* Final Answer */}
      {result && (
        <div role="region" aria-live="polite" style={{ marginTop: 20 }}>
          <h2>Answer</h2>
          <p>{result}</p>
        </div>
      )}

      {/* Visually Hidden Live Region */}
      <div
        aria-live="polite"
        style={{
          position: "absolute",
          left: "-10000px",
          width: "1px",
          height: "1px",
          overflow: "hidden"
        }}
      >
        {liveMessage}
      </div>
    </div>
  );
}

export default App;
