import { auth } from "../../auth";

export const executeGet = async <T>(
    path: string,
    searchParams?: URLSearchParams,
    revalidate: false | 0 | number = 0
): Promise<T> => {
    let endpoint = process.env.URL_DOMAIN + path
    if (searchParams) {
        endpoint = endpoint + `?${searchParams.toString()}`
    }
    const session = await auth();

    const headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-auth-token": session?.accessToken ?? "",
        "user_id": session?.user.id
    };
    const response = await fetch(endpoint, {
        method: "GET",
        headers,
        next: { revalidate }
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
