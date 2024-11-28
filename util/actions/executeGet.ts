import { auth } from "../../auth";

export const executeGet = async <T>(
    path: string,
    searchParams?: URLSearchParams,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    additionalHeaders?: any,
    revalidate: false | 0 | number = 0
): Promise<T> => {
    let endpoint = process.env.URL_DOMAIN + path
    if (searchParams) {
        endpoint = endpoint + `?${searchParams.toString()}`
    }
    console.log(endpoint)
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
        next: { revalidate }
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
