import { useEffect, useState } from "react";
import { api, type AccountOption, type DocumentInfo } from "../api";

const DOC_TYPES = ["support_policy", "sop", "product_guide", "agreement", "other"];
const AUTHORITY_LABEL = ["Agreement", "Current policy", "—", "Deprecated"];

export function DocumentsView({ sessionId, accounts }: { sessionId: string; accounts: AccountOption[] }) {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [status, setStatus] = useState<"current" | "deprecated">("current");
  const [accountScope, setAccountScope] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  function load() {
    setLoading(true);
    api
      .listDocuments(sessionId)
      .then(setDocs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [sessionId]);

  async function upload() {
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    setError(null);
    try {
      const result = await api.uploadDocument(sessionId, file, docType, status, accountScope);
      setUploadMsg(`Ingested ${result.chunks_ingested} chunk(s) from ${result.source_file}.`);
      setFile(null);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="docs-view">
      <div className="docs-upload">
        <div className="docs-upload-title">Add a document</div>
        <div className="docs-upload-row">
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <select value={docType} onChange={(e) => setDocType(e.target.value)}>
            {DOC_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value as "current" | "deprecated")}>
            <option value="current">Current</option>
            <option value="deprecated">Deprecated</option>
          </select>
          <select value={accountScope} onChange={(e) => setAccountScope(e.target.value)}>
            <option value="">All accounts</option>
            {accounts.map((a) => (
              <option key={a.account_id} value={a.account_id}>
                {a.account_name} only
              </option>
            ))}
          </select>
          <button className="btn-primary" onClick={upload} disabled={!file || uploading}>
            {uploading ? "Uploading…" : "Upload & ingest"}
          </button>
        </div>
        {uploadMsg && <div className="docs-upload-msg">{uploadMsg}</div>}
        {error && <div className="ops-error">{error}</div>}
      </div>

      <div className="docs-list-title">Documents in the knowledge base</div>
      {loading ? (
        <div className="ops-empty">Loading…</div>
      ) : docs.length === 0 ? (
        <div className="ops-empty">No documents ingested yet.</div>
      ) : (
        <div className="docs-table-wrap">
          <table className="docs-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Type</th>
                <th>Status</th>
                <th>Scope</th>
                <th>Authority</th>
                <th>Chunks</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.source_file}>
                  <td>{d.source_file}</td>
                  <td>{d.doc_type.replace(/_/g, " ")}</td>
                  <td>{d.status}</td>
                  <td>{d.account_scope ?? "All accounts"}</td>
                  <td>{AUTHORITY_LABEL[d.authority_rank] ?? d.authority_rank}</td>
                  <td>{d.chunk_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
