import "./App.css";

import Sidebar from "./components/Sidebar";
import Upload from "./components/Upload";
import Chat from "./components/Chat";
import Input from "./components/Input";

import useChat from "./hooks/useChat";

function App() {

  const { messages, loading, send } = useChat();

  return (

    <div className="layout">

      <Sidebar />

      <main className="main">

        <header className="topbar">

          <div className="logo">
            🔱
          </div>

          <div>

            <h1>TRIDENT AI</h1>

            <p>
              Intelligence • Recherche • Documents
            </p>

          </div>

        </header>

        <Upload />

        <Chat
          messages={messages}
          loading={loading}
        />

        <Input
          onSend={send}
          disabled={loading}
        />

      </main>

    </div>

  );

}

export default App;
