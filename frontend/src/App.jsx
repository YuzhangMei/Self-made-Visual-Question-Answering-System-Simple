import { useState } from "react";

function App() {
  const [imageFile, setImageFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("onepass");
  const [result, setResult] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();

    if (!imageFile || !question.trim()) {
      alert("Please upload an image and enter a question.");
      return;
    }

    setLoading(true);
    setResult(null);
    setClarification(null);
    setSessionId(null);

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
    } else {
      setResult(data.answer);
    }
  }

  async function handleClarifySelection(option) {
    setLoading(true);

    const res = await fetch("http://localhost:5000/clarify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
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
      <h1>Ambiguity-Aware VQA</h1>

      <form onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
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
        <br /><br />

        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="onepass">One-pass</option>
          <option value="clarify">Clarify</option>
        </select>

        <button type="submit" style={{ marginLeft: 10 }}>
          {loading ? "Processing..." : "Submit"}
        </button>
      </form>

      {/* Clarification Section */}
      {clarification && (
        <div>
          <h3>{clarification.question}</h3>
          {clarification.options.map((option, index) => (
            <button
              key={index}
              onClick={() => handleClarifySelection(option)}
              style={{
                display: "block",
                margin: "10px 0",
                padding: "10px",
              }}
              aria-label={`Select option ${option}`}
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
