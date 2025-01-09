/* eslint-disable @typescript-eslint/no-explicit-any */

import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { jwtDecode } from "jwt-decode";
import { signInSchema } from "./util/validations";
import { refreshAccessToken } from "./util/primatives/tokenUtil";
import { RoutePath } from "./objects/enum";

export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [
        Credentials({
            name: "Credentials",
            credentials: {
                email: { label: "Email", type: "email" },
                password: { label: "Password", type: "password" },
            },

            async authorize(credentials) {
                if (credentials === null) return null;

                try {
                    const { email, password } =
                        await signInSchema.parseAsync(credentials);

                    const response = await fetch(RoutePath.Login, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            email: email,
                            password: password,
                        })
                    }).then((response: any) => response.json())


                    return {
                        accessToken: response.accessToken,
                        refreshToken: response.refreshToken,
                        id: response.id,
                        role: response.role,
                        email: response.email,
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
        signIn: "/",
    },

    callbacks: {
        async jwt({ user, token }) {
            if (user) {
                return {
                    ...token,
                    accessToken: user.accessToken,
                    refreshToken: user.refreshToken,
                    user,
                };
            }

            if (token.accessToken) {
                const decodedToken = jwtDecode(token.accessToken);
                const exp = decodedToken?.exp ? decodedToken.exp * 1000 : 0;
                token.accessTokenExp = exp;
            }

            if (Date.now() < token.accessTokenExp) return token;

            return refreshAccessToken(token);
        },

        async session(value) {
            const { session, token } = value;
            if (token) {
                session.accessToken = token.accessToken;
                session.user = token.user;
            }
            return session;
        },
    },

    debug: process.env.NODE_ENV === "development",

    session: {
        strategy: "jwt",
    },
});
