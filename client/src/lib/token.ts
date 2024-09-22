import { JWT } from "next-auth/jwt";
import { PUBLIC_ROUTES } from "./routes";

export async function refreshAccessToken(token: JWT) {

   try {
      const url = process.env.URL_DOMAIN + PUBLIC_ROUTES.REFRESH_TOKEN

      const response = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${token.refreshToken}`
        }
      });
  
      const tokens = await response.json();
  
      if (!response.ok) {
        throw tokens;
      }
      return {
        ...token,
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken ?? token.refreshToken, // Fall back to old refresh token
      };
    } catch (error) {
      console.log(error);
  
      return {
        ...token,
        error: "RefreshAccessTokenError",
      };
    }
  }