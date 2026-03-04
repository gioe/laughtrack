/* eslint-disable @typescript-eslint/no-explicit-any */

import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter"
import Google from 'next-auth/providers/google'
import Apple from 'next-auth/providers/apple'
import Nodemailer from 'next-auth/providers/nodemailer'
import { db, prisma } from "./lib/db";
import { JWT } from "next-auth/jwt";

// Define session types
interface UserProfile {
    id: string;
    userid: string;
    role: string;
    emailShowNotifications: boolean;
}

declare module "next-auth" {
    interface Session {
        profile: UserProfile | null;
        user?: {
            id: string;
            email?: string | null;
        };
    }

    interface JWT {
        profile?: UserProfile;
    }
}

// Ensure Prisma client is initialized before using it
if (!prisma) {
    throw new Error('Prisma client is not initialized');
}

if (process.env.NODE_ENV === 'production') {
    if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASSWORD) {
        throw new Error('SMTP_HOST, SMTP_USER, and SMTP_PASSWORD must be set for email sign-in');
    }
}

const adapter = PrismaAdapter(prisma);

export const { handlers, signIn, signOut, auth } = NextAuth({
    adapter,
    providers: [
        Google,
        Apple,
        Nodemailer({
            id: "email",
            server: {
                host: process.env.SMTP_HOST ?? "",
                port: Number(process.env.SMTP_PORT) || 587,
                secure: process.env.SMTP_SECURE === 'true',
                auth: {
                    user: process.env.SMTP_USER ?? "",
                    pass: process.env.SMTP_PASSWORD ?? "",
                },
            },
            from: process.env.EMAIL_FROM ?? "noreply@laughtrack.com",
        }),
    ],
    secret: process.env.NEXTAUTH_SECRET,
    session: {
        strategy: "jwt",
        maxAge: 30 * 24 * 60 * 60, // 30 days
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
            if (token.sub) {
                try {
                    // Fetch the user profile only if we don't have it in the token
                    if (!token.profile) {
                        const profile = await prisma.userProfile.findUnique({
                            where: { userid: token.sub },
                        });
                        if (profile) {
                            // Store profile in token to avoid fetching it again
                            token.profile = profile;
                        }
                    }

                    // Add profile to session
                    session.profile = token.profile as UserProfile;
                } catch (error) {
                    console.error('Error fetching user profile:', error);
                }
            }
            return session;
        },
        async jwt({ token, user, trigger }) {
            if (user) {
                token.sub = user.id;
                // Fetch and store profile in token on initial sign in
                const profile = await prisma.userProfile.findUnique({
                    where: { userid: user.id },
                });
                if (profile) {
                    token.profile = profile;
                }
            }

            // If it's a session update, refresh the profile
            if (trigger === "update") {
                const profile = await prisma.userProfile.findUnique({
                    where: { userid: token.sub! },
                });
                if (profile) {
                    token.profile = profile;
                }
            }

            return token;
        }
    },
    pages: {
        signIn: '/',
    },
});
