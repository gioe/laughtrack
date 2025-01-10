import { auth } from "../../auth";
import { getBaseUrl } from "../urlUtil";

export const executeGet = async <T>(
    path: string,
    searchParams?: URLSearchParams,
    revalidate: false | 0 | number = 0
): Promise<T> => {
    console.log(path)
    let url = searchParams ? path + `?${searchParams.toString()}` : path

    const session = await auth();

    const headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-auth-token": session?.accessToken ?? "",
        "user_id": session?.user.id
    };
    const response = await fetch(getBaseUrl() + url, {
        method: "GET",
        headers,
        next: { revalidate }
    });

    if (!response.ok) throw new Error("Fetch Error");

    const data = await response.json();
    return data;
};
