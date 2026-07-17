import { useState } from "react";
import { sendMessage } from "../services/api";

export default function useChat() {
  const [messages, setMessages] = useState([
    {
      role: "ai",
      text: "Bonjour 👋 Je suis votre assistant IA."
    }
  ]);

  const [loading, setLoading] = useState(false);

  async function send(text) {
    if (!text.trim()) return;

    setMessages((old) => [
      ...old,
      {
        role: "user",
        text,
      },
    ]);

    setLoading(true);

    try {
      const data = await sendMessage(text);

      setMessages((old) => [
        ...old,
        {
          role: "ai",
          text: data.reply,
        },
      ]);
    } catch (err) {
      setMessages((old) => [
        ...old,
        {
          role: "ai",
          text: "❌ Impossible de contacter le serveur.",
        },
      ]);
    }

    setLoading(false);
  }

  return {
    messages,
    loading,
    send,
  };
}
