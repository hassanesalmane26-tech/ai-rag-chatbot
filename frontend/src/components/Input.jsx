import { useState } from "react";

function Input({ onSend, disabled }) {
  const [message, setMessage] = useState("");

  function handleSend() {
    if (!message.trim()) return;

    onSend(message);
    setMessage("");
  }

  return (
    <footer className="footer">

      <input
        type="text"
        placeholder="Posez votre question..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            handleSend();
          }
        }}
        disabled={disabled}
      />

      <button
        onClick={handleSend}
        disabled={disabled}
      >
        Envoyer
      </button>

    </footer>
  );
}

export default Input;
