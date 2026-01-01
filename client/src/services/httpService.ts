// httpService.ts (Updated postRequest)

const API_BASE_URL = 'http://localhost:8000'; // Use environment variable if you have one

// Generic type for API response (optional: you could make this more robust but current usage works)
// type ApiResponse<T> = Promise<T | { error: string }>;

export const postRequest = async <TRequest, TResponse>(
    path: string, // Changed from endpoint to path for consistency with getRequest
    body: TRequest
): Promise<TResponse | { error: string }> =>{ // Changed return type to union for explicit error object
    const url = `${API_BASE_URL}${path}`;
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            // Try to parse error message from JSON, fallback to status text
            const errorText = await response.text();
            let errorMessage = `HTTP error! Status: ${response.status}`;
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorJson.error || errorMessage;
            } catch {
                errorMessage = errorText || errorMessage; // Use raw text if not JSON
            }
            return { error: errorMessage }; // Return error object
        }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await response.json() as TResponse;
        } else {
            // If expecting TResponse as a simple string (e.g., UUID from /sessions)
            const textResponse = await response.text();
            // Attempt to parse as JSON first in case it's stringified JSON, then fall back to plain text
            try {
                return JSON.parse(textResponse) as TResponse;
            } catch {
                return textResponse as TResponse; // Return as plain text for string responses (like UUID)
            }
        }
    } catch (error: any) {
        console.error(`Error in POST request to ${url}:`, error);
        // Ensure error object is returned even for network issues
        return { error: error.message || 'Network error' };
    }
};

// getRequest looks good already, as you've already added the text/json handling
export async function getRequest<TResponse>(
    path: string
): Promise<TResponse | { error: string }> { // Changed return type to union for explicit error object
    const url = `${API_BASE_URL}${path}`;
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage = `HTTP error! Status: ${response.status}`;
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorJson.error || errorMessage;
            } catch {
                errorMessage = errorText || errorMessage;
            }
            return { error: errorMessage };
        }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await response.json() as TResponse;
        } else {
            const textResponse = await response.text();
            try {
                return JSON.parse(textResponse) as TResponse;
            } catch {
                return textResponse as TResponse;
            }
        }
    } catch (error: any) {
        console.error(`Error in GET request to ${url}:`, error);
        return { error: error.message || 'Network error' };
    }
}