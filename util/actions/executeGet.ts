import { auth } from "../../auth";

export const executeGet = async <T>(
    endpoint: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    additionalHeaders?: any,
): Promise<T> => {
    const session = await auth();

    let headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-auth-token": session?.accessToken ?? "",
    };

    if (additionalHeaders) {
        headers = {
            ...headers,
            ...additionalHeaders,
        };
    }

    const response = await fetch(endpoint, {
        method: "GET",
        headers,
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
