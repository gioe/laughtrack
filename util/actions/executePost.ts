import { JWT } from "next-auth/jwt";
import { auth } from "../../auth";
import { getBaseUrl } from "../urlUtil";

export const executePost = async <T>(
    url: string,
    body?: URLSearchParams,
    token?: JWT
): Promise<T> => {
    console.log(url)
    const session = await auth();

    const response = await fetch(getBaseUrl() + url, {
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
