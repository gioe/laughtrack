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
    events: {
        createUser: async ({ user }) => {
          // When a new user is created, create their profile
          await db.userProfile.create({
            data: {
              userId: user.id!,
              role: "user",
              emailShowNotifications: false,
            },
          });
        },
      },
    callbacks: {
        async  session({ session }) {
            console.log(session)
            if (session?.user) {
                // Optionally fetch and include the user profile
                const profile = await prisma.userProfile.findUnique({
                  where: { userId: session.user.id },
                });
                session.profile = {
                    email: session.user.email,
                    ...profile
                };
              }
              return session;
          },

    },

    debug: process.env.NODE_ENV !== "production",
    session: {
        strategy: "database",
        maxAge: 30 * 24 * 60 * 60
    },
});
