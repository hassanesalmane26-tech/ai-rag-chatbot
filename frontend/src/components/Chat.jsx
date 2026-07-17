import Message from "./Message";

function Chat({ messages, loading }) {
  return (
    <main className="chat">
      {messages.map((msg, index) => (
        <Message
          key={index}
          role={msg.role}
          content={msg.text}
        />
      ))}

      {loading && (
        <Message
          role="ai"
          content="🤖 IA en train de réfléchir..."
        />
      )}
    </main>
  );
}

export default Chat;
