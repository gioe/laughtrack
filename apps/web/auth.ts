/// <reference types="react/canary" />
import { cache } from "react";
import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter";
import Google from "next-auth/providers/google";
import Apple from "next-auth/providers/apple";
import Nodemailer from "next-auth/providers/nodemailer";
import { db, prisma } from "./lib/db";

// Define session types
interface UserProfile {
    id: string;
    userid: string;
    role: string;
    emailShowNotifications: boolean;
    zipCode?: string | null;
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

const adapter = PrismaAdapter(prisma);

const _nextAuth = NextAuth({
    adapter,
    providers: [
        Google,
        Apple,
        Nodemailer({
            id: "email",
            server: {
                host: process.env.SMTP_HOST ?? "",
                port: Number(process.env.SMTP_PORT) || 587,
                secure: process.env.SMTP_SECURE === "true",
                auth: {
                    user: process.env.SMTP_USER ?? "",
                    pass: process.env.SMTP_PASSWORD ?? "",
                },
            },
            from: process.env.EMAIL_FROM ?? "noreply@laughtrack.com",
        }),
    ],
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
                console.error("Error creating user profile:", error);
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
                    console.error("Error fetching user profile:", error);
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
        },
    },
    pages: {
        signIn: "/",
        error: "/",
    },
});

export const handlers = _nextAuth.handlers;
export const signIn = _nextAuth.signIn;
export const signOut = _nextAuth.signOut;
// React cache() request-scopes the no-arg result so multiple `await auth()`
// calls in the same request reuse the resolved session — avoiding duplicate
// session-callback runs and (on a cold JWT) duplicate userProfile lookups.
export const auth = cache(_nextAuth.auth);
