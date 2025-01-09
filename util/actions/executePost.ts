import { JWT } from "next-auth/jwt";
import { auth } from "../../auth";

export const executePost = async <T>(
    endpoint: string,
    body?: URLSearchParams,
    token?: JWT
): Promise<T> => {
    const session = await auth();

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-auth-token": session?.accessToken ?? "",
            "user_id": session?.user.id,
            ...(token ? { Authorization: `Bearer ${token.refreshToken}` } : {})
        }
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
