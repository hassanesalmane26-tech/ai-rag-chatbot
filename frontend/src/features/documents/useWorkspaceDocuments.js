import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteDocument as deleteDocumentRequest,
  listDocuments,
  uploadDocument as uploadDocumentRequest,
} from "../../services/api";
import {
  acceptsDocumentResult,
  prependDocument,
  removeDocumentById,
  validateDocumentFile,
} from "./documentState";

export default function useWorkspaceDocuments(workspaceId) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const workspaceRef = useRef(workspaceId);
  const requestVersionRef = useRef(0);

  const refresh = useCallback(async () => {
    if (!workspaceId) {
      setDocuments([]);
      setLoading(false);
      return [];
    }
    const request = ++requestVersionRef.current;
    setLoading(true);
    setError("");
    try {
      const values = await listDocuments(workspaceId);
      if (request !== requestVersionRef.current || !acceptsDocumentResult(workspaceRef.current, workspaceId)) return [];
      setDocuments(values);
      return values;
    } catch (err) {
      if (request === requestVersionRef.current && acceptsDocumentResult(workspaceRef.current, workspaceId)) setError(err.message);
      return [];
    } finally {
      if (request === requestVersionRef.current && acceptsDocumentResult(workspaceRef.current, workspaceId)) setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    workspaceRef.current = workspaceId;
    requestVersionRef.current += 1;
    setDocuments([]);
    setError("");
    setUploading(false);
    setDeletingId(null);
    refresh();
    return () => { requestVersionRef.current += 1; };
  }, [workspaceId, refresh]);

  const uploadDocument = useCallback(async (file) => {
    const validationError = validateDocumentFile(file);
    if (validationError) {
      setError(validationError);
      return false;
    }
    const requestWorkspaceId = workspaceId;
    if (!requestWorkspaceId || uploading) return false;
    setUploading(true);
    setError("");
    try {
      const document = await uploadDocumentRequest(requestWorkspaceId, file);
      if (acceptsDocumentResult(workspaceRef.current, requestWorkspaceId)) {
        setDocuments((current) => prependDocument(current, document));
      }
      return true;
    } catch (err) {
      if (acceptsDocumentResult(workspaceRef.current, requestWorkspaceId)) setError(err.message);
      return false;
    } finally {
      if (acceptsDocumentResult(workspaceRef.current, requestWorkspaceId)) setUploading(false);
    }
  }, [workspaceId, uploading]);

  const deleteDocument = useCallback(async (documentId) => {
    const requestWorkspaceId = workspaceId;
    if (!requestWorkspaceId || deletingId) return false;
    setDeletingId(documentId);
    setError("");
    try {
      await deleteDocumentRequest(requestWorkspaceId, documentId);
      if (acceptsDocumentResult(workspaceRef.current, requestWorkspaceId)) {
        setDocuments((current) => removeDocumentById(current, documentId));
      }
      return true;
    } catch (err) {
      if (acceptsDocumentResult(workspaceRef.current, requestWorkspaceId)) setError(err.message);
      return false;
    } finally {
      if (acceptsDocumentResult(workspaceRef.current, requestWorkspaceId)) setDeletingId(null);
    }
  }, [workspaceId, deletingId]);

  return { documents, loading, uploading, deletingId, error, refresh, uploadDocument, deleteDocument };
}
