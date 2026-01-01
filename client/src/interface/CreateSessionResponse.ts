export interface CreateSessionResponse {
    session_id: string; // The backend returns a UUID string
    title: string;
    created_at: string;
    last_updated: string;
}