"use server";

import { getSession } from "./getSession";

export async function getCurrentUser() {
    try {
        const session = await getSession();

        if (!session?.user?.email) {
            return null;
        }

        return {
            id: session.user.id,
            email: session.user.email,
            role: session.user.role
        }
    }
    catch (error) {
        return null;
    }

}