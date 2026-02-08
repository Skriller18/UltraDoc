import React, { useMemo, useState } from "react";

function Row({ item }) {
  return (
    <div className="debug-row">
      <div className="debug-cell rank">#{item.rank}</div>
      <div className="debug-cell score">
        <div>sim: {item.similarity?.toFixed?.(3) ?? item.similarity}</div>
        {item.keyword_score !== undefined && (
          <div>kw: {item.keyword_score?.toFixed?.(3) ?? item.keyword_score}</div>
        )}
        {item.rerank_score !== undefined && (
          <div>rerank: {item.rerank_score?.toFixed?.(3) ?? item.rerank_score}</div>
        )}
      </div>
      <div className="debug-cell meta">
        <div>page: {item.page_num ?? "—"}</div>
        <div>chunk: {item.chunk_index ?? "—"}</div>
      </div>
      <div className="debug-cell preview">
        <div className="debug-preview">{item.preview}</div>
        {item.chunk_id && <div className="debug-chunkid">{item.chunk_id}</div>}
      </div>
    </div>
  );
}

export function DebugRetrievalPanel({ data, onRefresh, isLoading }) {
  const [open, setOpen] = useState(true);

  const hasError = Boolean(data?.error);

  const raw = useMemo(() => data?.raw_top || [], [data]);
  const reranked = useMemo(() => data?.reranked_top || [], [data]);

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <button className="debug-toggle" onClick={() => setOpen((v) => !v)}>
          {open ? "▼" : "▶"} Debug: retrieval
        </button>
        <div className="debug-actions">
          <button className="action-btn secondary" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {open && (
        <div className="debug-body">
          <div className="debug-summary">
            <div>
              <span className="muted">doc:</span> {data?.document_id || "—"}
            </div>
            <div>
              <span className="muted">top_k:</span> {data?.top_k ?? "—"} <span className="muted">pre_k:</span>{" "}
              {data?.pre_k ?? "—"}
            </div>
          </div>

          {hasError && (
            <div className="debug-error">
              <div className="debug-error-title">Not searchable yet</div>
              <div className="debug-error-text">{data.error.message}</div>
              {data.error.missing?.length > 0 && (
                <div className="debug-error-text">
                  Missing: <code>{data.error.missing.join(", ")}</code>
                </div>
              )}
            </div>
          )}

          <div className="debug-columns">
            <div className="debug-col">
              <div className="debug-col-title">Raw (FAISS)</div>
              {raw.length === 0 ? (
                <div className="muted">No results</div>
              ) : (
                raw.map((item, idx) => <Row key={`raw_${idx}`} item={item} />)
              )}
            </div>

            <div className="debug-col">
              <div className="debug-col-title">Reranked (hybrid)</div>
              {reranked.length === 0 ? (
                <div className="muted">No results</div>
              ) : (
                reranked.map((item, idx) => <Row key={`rr_${idx}`} item={item} />)
              )}
            </div>
          </div>

          {data?.question && (
            <div className="debug-question">
              <span className="muted">q:</span> {data.question}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
