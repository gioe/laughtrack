import { auth } from "../auth";

export const executePost = async <T>(
    endpoint: string,
    body?: any,
): Promise<T> => {
    const session = await auth();

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-auth-token": session?.accessToken ?? "",
        },
        body: new URLSearchParams(body),
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
