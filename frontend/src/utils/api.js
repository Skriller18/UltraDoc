export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const getDocumentUrl = (documentId) =>
  `${API_BASE}/documents/${documentId}/file`;

export const api = {
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Upload failed");
    }

    return response.json();
  },

  async askQuestion(documentId, question) {
    const response = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        document_id: documentId,
        question: question,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to get answer");
    }

    return response.json();
  },

  async extractData(documentId) {
    const response = await fetch(`${API_BASE}/extract`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        document_id: documentId,
      }),
    });

    if (!response.ok) {
      throw new Error("Extraction failed");
    }

    return response.json();
  },
};
