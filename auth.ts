/* eslint-disable @typescript-eslint/no-explicit-any */

import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter"
import Google from 'next-auth/providers/google'
import Apple from 'next-auth/providers/apple'
import { db, prisma } from "./lib/db";

// Ensure Prisma client is initialized before using it
if (!prisma) {
  throw new Error('Prisma client is not initialized');
}

const adapter = PrismaAdapter(prisma)

export const { handlers, signIn, signOut, auth } = NextAuth({
    adapter,
    providers: [Google, Apple],
    secret: process.env.NEXTAUTH_SECRET,
    session: {
        strategy: "jwt"
    },
    events: {
        createUser: async ({ user }) => {
          try {
            // When a new user is created, create their profile
            await db.userProfile.create({
              data: {
                userid: user.id!,
                role: "user",
                emailShowNotifications: false,
              },
            });
          } catch (error) {
            console.error('Error creating user profile:', error);
          }
        },
    },
    callbacks: {
        async session({ session, token }) {
            if (session?.user) {
                try {
                  // Optionally fetch and include the user profile
                  const profile = await prisma.userProfile.findUnique({
                    where: { userid: token.sub },
                  });
                  session.profile = {
                      email: session.user.email,
                      ...profile
                  };
                } catch (error) {
                  console.error('Error fetching user profile:', error);
                  // Don't fail the session if profile fetch fails
                }
            }
            return session;
        },
        async jwt({ token, user }) {
            if (user) {
                token.sub = user.id;
            }
            return token;
        }
    },
    pages: {
        signIn: '/',
    },
});
