/// <reference types="react/canary" />
import { cache } from "react";
import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter";
import Google from "next-auth/providers/google";
import Apple from "next-auth/providers/apple";
import Nodemailer from "next-auth/providers/nodemailer";
import { createTransport } from "nodemailer";
import { db, prisma } from "./lib/db";
import {
    appleProviderConfig,
    googleProviderConfig,
} from "@/lib/auth/providerConfig";
import { sanitizeAuthError } from "@/lib/auth/authErrorLogging";
import {
    buildMagicLinkEmail,
    buildWelcomeEmail,
} from "@/lib/auth/emailTemplate";

// Define session types
interface UserProfile {
    id: string;
    userid: string;
    role: string;
    emailShowNotifications: boolean;
    pushShowNotifications: boolean;
    zipCode?: string | null;
    nearbyDistanceMiles?: number | null;
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
const emailServer = {
    host: process.env.SMTP_HOST ?? "",
    port: Number(process.env.SMTP_PORT) || 587,
    secure: process.env.SMTP_SECURE === "true",
    auth: {
        user: process.env.SMTP_USER ?? "",
        pass: process.env.SMTP_PASSWORD ?? "",
    },
};
const emailFrom = process.env.EMAIL_FROM ?? "noreply@laughtrack.com";

// Apple sign-in uses response_mode=form_post: appleid.apple.com POSTs the auth
// response back to our callback as a cross-site POST. Browsers drop
// SameSite=Lax cookies on cross-site POSTs, so Auth.js's default Lax
// `callback-url` cookie is lost on the Apple round-trip — NextAuth then falls
// back to baseUrl and the native iOS flow is stranded on the web home page
// instead of redirecting to the `laughtrack://auth/callback` deep link
// (manifested as "Apple sign-in logs me in on web but never returns to the
// app"). Auth.js already sets the state & nonce cookies to SameSite=None for
// exactly this reason; we extend the same treatment to the callbackUrl cookie
// so the native callback target survives the POST. SameSite=None requires
// Secure (HTTPS only), so dev over http keeps the Lax default. Google is
// unaffected — its GET callback is a top-level navigation that carries Lax
// cookies — but aligning the cookie is harmless for it.
const useSecureCookies = process.env.NODE_ENV === "production";
const cookiePrefix = useSecureCookies ? "__Secure-" : "";

const _nextAuth = NextAuth({
    adapter,
    logger: {
        error(error) {
            console.error(
                "Auth.js error",
                JSON.stringify(sanitizeAuthError(error)),
            );
        },
    },
    providers: [
        Google(googleProviderConfig()),
        Apple(appleProviderConfig()),
        Nodemailer({
            id: "email",
            server: emailServer,
            from: emailFrom,
            async sendVerificationRequest({ identifier, url, provider }) {
                const transport = createTransport(provider.server);
                const email = buildMagicLinkEmail({ url });
                const result = await transport.sendMail({
                    to: identifier,
                    from: provider.from,
                    subject: email.subject,
                    text: email.text,
                    html: email.html,
                });
                const failed = [
                    ...(result.rejected || []),
                    ...(result.pending || []),
                ].filter(Boolean);
                if (failed.length) {
                    throw new Error(
                        `Email (${failed.join(", ")}) could not be sent`,
                    );
                }
            },
        }),
    ],
    session: {
        strategy: "jwt",
        maxAge: 30 * 24 * 60 * 60, // 30 days
    },
    cookies: {
        callbackUrl: {
            name: `${cookiePrefix}authjs.callback-url`,
            options: {
                httpOnly: true,
                sameSite: useSecureCookies ? "none" : "lax",
                path: "/",
                secure: useSecureCookies,
            },
        },
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
                        pushShowNotifications: false,
                    },
                });
            } catch (error) {
                console.error(
                    "Error creating user profile:",
                    JSON.stringify(sanitizeAuthError(error)),
                );
                return;
            }

            const verifiedUser = user as typeof user & {
                emailVerified?: Date | null;
            };
            if (!user.email || !verifiedUser.emailVerified) {
                return;
            }

            try {
                const transport = createTransport(emailServer);
                const email = buildWelcomeEmail({ baseUrl: getSiteBaseUrl() });
                const result = await transport.sendMail({
                    to: user.email,
                    from: emailFrom,
                    subject: email.subject,
                    text: email.text,
                    html: email.html,
                });
                const failed = [
                    ...(result.rejected || []),
                    ...(result.pending || []),
                ].filter(Boolean);
                if (failed.length) {
                    throw new Error(
                        `Welcome email (${failed.join(", ")}) could not be sent`,
                    );
                }
            } catch (error) {
                console.error(
                    "Error sending welcome email:",
                    JSON.stringify(sanitizeAuthError(error)),
                );
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
                    console.error(
                        "Error fetching user profile:",
                        JSON.stringify(sanitizeAuthError(error)),
                    );
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

function getSiteBaseUrl(): string {
    if (process.env.NEXT_PUBLIC_WEBSITE_URL) {
        return process.env.NEXT_PUBLIC_WEBSITE_URL;
    }
    if (process.env.AUTH_URL) {
        return process.env.AUTH_URL;
    }
    if (process.env.VERCEL_URL) {
        return `https://${process.env.VERCEL_URL}`;
    }
    return "http://localhost:3000";
}
