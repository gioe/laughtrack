import { auth } from "../../auth";

export const executeGet = async <T>(
    path: string,
    searchParams?: URLSearchParams,
    revalidate: false | 0 | number = 0
): Promise<T> => {
    let url = searchParams ? path + `?${searchParams.toString()}` : path

    const session = await auth();

    const headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-auth-token": session?.accessToken ?? "",
        "user_id": session?.user.id
    };
    const response = await fetch(getBaseUrl(), {
        method: "GET",
        headers,
        next: { revalidate }
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};

const getBaseUrl = () => {
    if (typeof window !== 'undefined') {
        // Browser should use relative path
        return '';
    }

    if (process.env.VERCEL_URL) {
        // Reference for vercel.com
        return `https://${process.env.VERCEL_URL}`;
    }

    if (process.env.RENDER_INTERNAL_HOSTNAME) {
        // Reference for render.com
        return `http://${process.env.RENDER_INTERNAL_HOSTNAME}:${process.env.PORT}`;
    }

    // Assume localhost
    return `http://localhost:${process.env.PORT || 3000}`;
};
