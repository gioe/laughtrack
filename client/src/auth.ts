import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { PUBLIC_ROUTES } from "./lib/routes";
import { jwtDecode } from "jwt-decode";
import { signInSchema } from "./lib/validations";
import { refreshAccessToken } from "./lib/token";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [

    Credentials({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },

      async authorize(credentials) {
        console.log("AUTHORIZING")
        console.log(credentials)

        if (credentials === null) return null;

        try {
          const { email, password } = await signInSchema.parseAsync(credentials)
          const url = process.env.URL_DOMAIN + PUBLIC_ROUTES.LOGIN

          const response = await fetch(url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
              email: email,
              password: password,
            }),
          })

          const jsonResponse = await response.json();

          return {
            accessToken: jsonResponse.data.accessToken,
            refreshToken: jsonResponse.data.refreshToken,
            role: jsonResponse.data.user.role,
            email: jsonResponse.data.user.email,
          };
        } catch (e) {
          console.error(e);
          return null;
        }
      },
    }),
  ],

  secret: process.env.NEXTAUTH_SECRET,

  pages: {
    signIn: '/'
  },

  callbacks: {

    async jwt({ token, account, user }) {

      if (token.accessToken) {
        const decodedToken = jwtDecode(token.accessToken);
        const exp = decodedToken?.exp ? decodedToken.exp * 1000 : 0;
        token.accessTokenExp = exp
      }

      if (account && user) {
        return {
          ...token,
          accessToken: user.accessToken,
          refreshToken: user.refreshToken,
          user,
        };
      }

      if (Date.now() < token.accessTokenExp) return token;

      return refreshAccessToken(token);
    },

    async session({ session, token }) {
      if (token) {
        session.accessToken = token.accessToken;
        session.user = token.user;
      }
      return session;
    },

  },

  debug: process.env.NODE_ENV === 'development',

  session: {
    strategy: 'jwt',
  },

});