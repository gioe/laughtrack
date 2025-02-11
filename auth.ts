/* eslint-disable @typescript-eslint/no-explicit-any */

import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter"
import Google from 'next-auth/providers/google'
import Apple from 'next-auth/providers/apple'
import { db, prisma } from "./lib/db";

export const { handlers, signIn, signOut, auth } = NextAuth({
    adapter: PrismaAdapter(prisma),

    providers: [Google, Apple],

    secret: process.env.NEXTAUTH_SECRET,

    pages: {
        signIn: "/",
    },

    callbacks: {
        async     session({ session, token }) {
            if (session.user) {
              // Add the user ID from the token to the session
              session.user.id = token.sub ?? ""
            }
            return session
          },

    },

    debug: process.env.NODE_ENV !== "production",

    session: {
        strategy: "jwt",
    },
});
