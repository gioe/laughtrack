import { JWT } from "next-auth/jwt";
import { RoutePath } from "../../objects/enum";

export async function refreshAccessToken(token: JWT) {
    return fetch(RoutePath.RefreshToken, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: `Bearer ${token.refreshToken}`,
        },
    })
        .then((response) => {
            if (response.ok) return response.json();
            throw new Error("Response not ok");
        })
        .then((data) => {
            return {
                ...token,
                accessToken: data.accessToken,
                refreshToken: data.refreshToken ?? token.refreshToken, // Fall back to old refresh token
            };
        })
        .catch((error) => {
            console.error(error);
            return {
                ...token,
                error: "RefreshAccessTokenError",
            };
        });
}
