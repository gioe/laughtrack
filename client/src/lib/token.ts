import { JWT } from "next-auth/jwt";
import { PUBLIC_ROUTES } from "./routes";

export async function refreshAccessToken(token: JWT) {
      const url = process.env.URL_DOMAIN + PUBLIC_ROUTES.REFRESH_TOKEN

      return fetch(url, {
        cache: 'no-store',
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          "Authorization": `Bearer ${token.refreshToken}`
        }
        })
        .then((response) => {
          if (response.ok) return response.json();
          throw new Error("Response not ok")
        })
        .then((data) => {
          return {
            ...token,
            accessToken: data.accessToken,
            refreshToken: data.refreshToken ?? token.refreshToken, // Fall back to old refresh token
          };
        })
        .catch((error) => {
          console.log(error)
          return {
            ...token,
            error: "RefreshAccessTokenError",
          };
        })

  }