import { JWT } from "next-auth/jwt";
import { APIRoutePath } from "../../objects/enum";
import { executePost } from "../actions/executePost";

export async function refreshAccessToken(token: JWT) {
    return executePost<Response>(APIRoutePath.TokenRefresh, undefined, token)
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
