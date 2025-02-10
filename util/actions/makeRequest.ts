import { JWT } from "next-auth/jwt";
import { getUrl } from "../urlUtil";
import { Session } from "next-auth";
import { RestAPIAction } from "../../objects/enum";

interface ExecuteOptions {
    method?: RestAPIAction;
    token?: JWT;
    body?: any;
    searchParams?: URLSearchParams;
    revalidate?: false | 0 | number;
    session?: Session | null;
    next?: NextFetchRequestConfig;  // Add this type for Next.js fetch options
}

export const makeRequest = async <T>(
    endpoint: string,
    options: ExecuteOptions = {}
): Promise<T> => {
    const {
        method = "GET",
        token,
        body,
        searchParams,
        revalidate = 0,
        session,
        next
    } = options;
    // Create base URL
    const url = getUrl(endpoint, searchParams)
    // Construct headers
    const headers: Record<string, string> = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-auth-token": session?.accessToken ?? "",
    };

    // Add authorization header if token provided
    if (token) {
        headers["Authorization"] = `Bearer ${token.refreshToken}`;
    }

    // Construct request options
    const requestOptions: RequestInit = {
        method,
        headers,
        next: {
            ...(next || {}),  // Allow passing in any next config options
            ...(method === "GET" ? { revalidate } : {}),  // Keep existing revalidation logic
            tags: [
                ...(next?.tags || []),  // Spread any tags passed in through next config
            ]
        }
    };

    // Add body for non-GET requests
    if (method !== "GET" && body) {
        requestOptions.body = body instanceof URLSearchParams
            ? body
            : JSON.stringify(body);
    }

    // Make request
    const response = await fetch(url, requestOptions);
    if (!response.ok) {
        throw new Error(`Fetch Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data;
};
