import { JWT } from "next-auth/jwt";
import { APIRoutePath, RestAPIAction } from "../../objects/enum";
import { makeRequest } from "../actions/makeRequest";
import { TokenRefreshResponse } from "@/app/api/token/refresh/interface";

export async function refreshAccessToken(token: JWT) {
    return makeRequest<TokenRefreshResponse>(APIRoutePath.TokenRefresh, {
        method: RestAPIAction.POST,
        token
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
