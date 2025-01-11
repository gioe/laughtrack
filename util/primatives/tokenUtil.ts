import { JWT } from "next-auth/jwt";
import { APIRoutePath, RestAPIAction } from "../../objects/enum";
import { makeRequest } from "../actions/makeRequest";

export async function refreshAccessToken(token: JWT) {
    return makeRequest<Response>(APIRoutePath.TokenRefresh, {
        method: RestAPIAction.POST,
        token
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
