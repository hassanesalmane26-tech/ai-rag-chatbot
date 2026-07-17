import { uploadDocument } from "../services/api";

function Upload() {

  async function handleFile(event) {

    const file = event.target.files[0];

    if (!file) return;

    try {

      const data = await uploadDocument(file);

      alert(
        `✅ ${data.message}\nChunks : ${data.chunks}`
      );

    } catch (err) {

      alert("❌ Erreur lors de l'upload.");

    }

  }

  return (

    <div style={{ padding: "10px" }}>

      <input
        type="file"
        accept=".pdf,.txt,.docx"
        onChange={handleFile}
      />

    </div>

  );

}

export default Upload;
