export interface AquiferSummaryResponse {
    cypher_query: string;
    record_count: number;
    ai_response: string;
    statistics: any;
    objectids: string[];
    session_id: string; // Backend returns it, so include it here
}