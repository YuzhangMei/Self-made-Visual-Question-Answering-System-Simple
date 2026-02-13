import { useState } from "react";

function App() {
  const [imageFile, setImageFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("onepass");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);


  async function handleSubmit(e) {
    e.preventDefault();

    if (!imageFile) {
      alert("Please choose an image first.");
      return;
    }
    if (!question.trim()) {
      alert("Please type a question.");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("image", imageFile);
      formData.append("question", question);
      formData.append("mode", mode);

      const res = await fetch("http://localhost:5000/analyze", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Backend error (${res.status}): ${text}`)
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 40, maxWidth: 900 }}>
      <h1>Project 11 – Phase 1 (Step 2)</h1>
      <p>Upload an image, ask a question, and send it to the Flask backend.</p>

      <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12 }}>
        <label>
          <div style={{ fontWeight: 600 }}>Image</div>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setImageFile(e.target.files?.[0] || null)}
            aria-label="Upload an image"
          />
        </label>

        <label>
          <div style={{ fontWeight: 600 }}>Question</div>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='e.g., "What is on the table?"'
            style={{ width: "100%", padding: 8 }}
            aria-label="Type your question"
          />
        </label>

        <label>
          <div style={{ fontWeight: 600 }}>Mode</div>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            style={{ padding: 8, width: 260 }}
            aria-label="Choose mode"
          >
            <option value="onepass">One-pass exhaustive response</option>
            <option value="clarify">Multi-turn clarification</option>
          </select>
        </label>

        <button
          type="submit"
          disabled={loading}
          style={{ padding: 10, width: 220 }}
          aria-label="Submit"
        >
          {loading ? "Sending..." : "Analyze"}
        </button>
      </form>

      <hr style={{ margin: "24px 0" }} />

      <h2>Backend Response (JSON)</h2>
      {result ? (
        <pre
          style={{
            background: "#f6f8fa",
            padding: 16,
            borderRadius: 8,
            overflowX: "auto",
          }}
        >
          {JSON.stringify(result, null, 2)}
        </pre>
      ) : (
        <p style={{ opacity: 0.7 }}>No result yet.</p>
      )}
    </div>
  );
}

export default App;