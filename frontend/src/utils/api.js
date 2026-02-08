export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const getDocumentUrl = (documentId) =>
  `${API_BASE}/documents/${documentId}/file`;

export const api = {
  async listDocuments() {
    const response = await fetch(`${API_BASE}/documents`);
    if (!response.ok) throw new Error("Failed to list documents");
    return response.json();
  },

  async deleteDocument(documentId) {
    const response = await fetch(`${API_BASE}/documents/${documentId}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to delete document");
    return response.json();
  },

  async debugRetrieve(documentId, question, { topK = 6 } = {}) {
    const url = new URL(`${API_BASE}/debug/retrieve`);
    url.searchParams.set("document_id", documentId);
    url.searchParams.set("q", question);
    url.searchParams.set("top_k", String(topK));

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error("Debug retrieve failed");
    return response.json();
  },

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

  async extractData(documentId, { force = false } = {}) {
    const response = await fetch(`${API_BASE}/extract`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        document_id: documentId,
        force,
      }),
    });

    if (!response.ok) {
      throw new Error("Extraction failed");
    }

    return response.json();
  },
};
