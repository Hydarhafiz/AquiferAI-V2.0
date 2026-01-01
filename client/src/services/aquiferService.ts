// src/api_services/aquiferService.ts
import type { AquiferSummaryRequest } from '../interface/AquiferSummaryRequest';
import type { AquiferSummaryResponse } from '../interface/AquiferSummaryResponse';
import { postRequest } from '../services/httpService';



export const getAquiferSummary = async (
    prompt: string,
    sessionId: string | null // Accept sessionId as a parameter
): Promise<AquiferSummaryResponse | { error: string }> => {
    return postRequest<AquiferSummaryRequest, AquiferSummaryResponse>(
        '/api/aquifer-summary',
        { question: prompt, session_id: sessionId || undefined } // Pass session_id
    );
};