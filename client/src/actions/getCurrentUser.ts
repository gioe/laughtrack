"use server";

import { getSession } from "./getSession";

export async function getCurrentUser() {
    try {
        const session = await getSession();

        if (!session?.user?.email) {
            return null;
        }

        return {
            id: 0,
            email: "",
            role: ""
        }
    }
    catch (error) {
        return null;
    }

}