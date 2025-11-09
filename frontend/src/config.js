// Shared configuration for backend base URL
// This is the single source of truth for the backend URL
export const BACKEND_BASE_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

