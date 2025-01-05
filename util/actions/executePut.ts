/* eslint-disable @typescript-eslint/no-explicit-any */
export const executePut = async <T>(
    endpoint: string,
    session: any,
    body?: any,
): Promise<T> => {
    const response = await fetch(endpoint, {
        method: "PUT",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-auth-token": session?.accessToken ?? "",
            "user_id": session?.data.user.id
        },
        body: JSON.stringify(body)
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
