import Header from "./components/navigation/Header";
import "./App.css";

import MainLayout from "./app/layout/MainLayout";

import Upload from "./components/Upload";
import Chat from "./components/Chat";
import Input from "./components/Input";

import useChat from "./hooks/useChat";

function App() {
  const { messages, loading, send } = useChat();

  return (
    <MainLayout>
    <Header />
      <Upload />

      <Chat
        messages={messages}
        loading={loading}
      />

      <Input
        onSend={send}
        disabled={loading}
      />
    </MainLayout>
  );
}

export default App;
