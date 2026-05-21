import { describe, it, expect, vi, beforeEach } from "vitest";

const {
    mockNextAuth,
    mockFindUnique,
    mockUserProfileCreate,
    mockCreateTransport,
    mockBuildMagicLinkEmail,
    capturedConfig,
} = vi.hoisted(() => {
    const captured: { value: any } = { value: null };
    const findUnique = vi.fn();
    const userProfileCreate = vi.fn();
    const createTransport = vi.fn();
    const buildMagicLink = vi.fn();
    const nextAuth = vi.fn((config: any) => {
        captured.value = config;
        return {
            handlers: { GET: vi.fn(), POST: vi.fn() },
            signIn: vi.fn(),
            signOut: vi.fn(),
            auth: vi.fn(),
        };
    });
    return {
        mockNextAuth: nextAuth,
        mockFindUnique: findUnique,
        mockUserProfileCreate: userProfileCreate,
        mockCreateTransport: createTransport,
        mockBuildMagicLinkEmail: buildMagicLink,
        capturedConfig: captured,
    };
});

vi.mock("react", async (importOriginal) => {
    const actual = await importOriginal<typeof import("react")>();
    return { ...actual, cache: <T,>(fn: T) => fn };
});
vi.mock("next-auth", () => ({ default: mockNextAuth }));
vi.mock("@auth/prisma-adapter", () => ({ PrismaAdapter: vi.fn(() => ({})) }));
vi.mock("next-auth/providers/google", () => ({
    default: vi.fn((config: unknown) => ({ id: "google", type: "oauth", config })),
}));
vi.mock("next-auth/providers/apple", () => ({
    default: vi.fn((config: unknown) => ({ id: "apple", type: "oauth", config })),
}));
vi.mock("next-auth/providers/nodemailer", () => ({
    default: vi.fn((config: any) => ({
        id: config?.id ?? "email",
        type: "email",
        ...config,
    })),
}));
vi.mock("nodemailer", () => ({ createTransport: mockCreateTransport }));
vi.mock("@/lib/auth/emailTemplate", () => ({
    buildMagicLinkEmail: mockBuildMagicLinkEmail,
}));
vi.mock("./lib/db", () => ({
    prisma: { userProfile: { findUnique: mockFindUnique } },
    db: {
        userProfile: {
            findUnique: mockFindUnique,
            create: mockUserProfileCreate,
        },
    },
}));

// Import after mocks so NextAuth() runs with the stub and captures the config.
import "./auth";

const PROFILE_ROW = {
    id: "profile-1",
    userid: "user-1",
    role: "user",
    emailShowNotifications: false,
    pushShowNotifications: false,
    zipCode: "11772",
    nearbyDistanceMiles: 25,
};

beforeEach(() => {
    mockFindUnique.mockReset();
    mockUserProfileCreate.mockReset();
    mockCreateTransport.mockReset();
    mockBuildMagicLinkEmail.mockReset();
});

describe("auth.ts NextAuth config", () => {
    it("captured a config object at module load", () => {
        expect(mockNextAuth).toHaveBeenCalledTimes(1);
        expect(capturedConfig.value).toBeTruthy();
        expect(capturedConfig.value.callbacks).toBeTruthy();
    });

    describe("providers admit Google, Apple, and Email", () => {
        // auth.ts has no explicit signIn callback — admittance is controlled
        // by the providers list. Asserting Google and Apple are configured is
        // the equivalent "signIn admits these providers" guarantee.
        it("includes Google and Apple OAuth providers and the email provider", () => {
            const providers = capturedConfig.value.providers as Array<{
                id: string;
                type: string;
            }>;
            const ids = providers.map((p) => p.id);
            expect(ids).toContain("google");
            expect(ids).toContain("apple");
            expect(ids).toContain("email");
        });
    });

    describe("session callback", () => {
        it("fetches the profile and maps it onto the session when token.profile is empty", async () => {
            mockFindUnique.mockResolvedValueOnce(PROFILE_ROW);
            const session: any = { profile: null, user: { id: "user-1" } };
            const token: any = { sub: "user-1" };

            const result = await capturedConfig.value.callbacks.session({
                session,
                token,
            });

            expect(mockFindUnique).toHaveBeenCalledWith({
                where: { userid: "user-1" },
            });
            expect(token.profile).toEqual(PROFILE_ROW);
            expect(result.profile).toEqual(PROFILE_ROW);
        });

        it("reuses token.profile without an extra db lookup when already cached", async () => {
            const session: any = { profile: null, user: { id: "user-1" } };
            const token: any = { sub: "user-1", profile: PROFILE_ROW };

            const result = await capturedConfig.value.callbacks.session({
                session,
                token,
            });

            expect(mockFindUnique).not.toHaveBeenCalled();
            expect(result.profile).toEqual(PROFILE_ROW);
        });

        it("leaves session.profile undefined when no profile row exists", async () => {
            mockFindUnique.mockResolvedValueOnce(null);
            const session: any = { profile: null, user: { id: "user-1" } };
            const token: any = { sub: "user-1" };

            const result = await capturedConfig.value.callbacks.session({
                session,
                token,
            });

            expect(mockFindUnique).toHaveBeenCalledTimes(1);
            expect(token.profile).toBeUndefined();
            expect(result.profile).toBeUndefined();
        });

        it("returns the session unchanged when token.sub is missing", async () => {
            const session: any = { profile: null };
            const token: any = {};

            const result = await capturedConfig.value.callbacks.session({
                session,
                token,
            });

            expect(mockFindUnique).not.toHaveBeenCalled();
            expect(result).toBe(session);
        });

        it("swallows lookup errors and still returns the session", async () => {
            const consoleSpy = vi
                .spyOn(console, "error")
                .mockImplementation(() => {});
            mockFindUnique.mockRejectedValueOnce(new Error("db down"));
            const session: any = { profile: null };
            const token: any = { sub: "user-1" };

            const result = await capturedConfig.value.callbacks.session({
                session,
                token,
            });

            expect(result).toBe(session);
            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();
        });
    });

    describe("jwt callback", () => {
        it("populates token.sub and token.profile on initial sign in", async () => {
            mockFindUnique.mockResolvedValueOnce(PROFILE_ROW);
            const token: any = {};
            const user: any = { id: "user-1" };

            const result = await capturedConfig.value.callbacks.jwt({
                token,
                user,
                trigger: "signIn",
            });

            expect(mockFindUnique).toHaveBeenCalledWith({
                where: { userid: "user-1" },
            });
            expect(result.sub).toBe("user-1");
            expect(result.profile).toEqual(PROFILE_ROW);
        });

        it("refreshes token.profile from prisma when trigger is 'update'", async () => {
            const updated = { ...PROFILE_ROW, zipCode: "10001" };
            mockFindUnique.mockResolvedValueOnce(updated);
            const token: any = { sub: "user-1", profile: PROFILE_ROW };

            const result = await capturedConfig.value.callbacks.jwt({
                token,
                trigger: "update",
            });

            expect(mockFindUnique).toHaveBeenCalledWith({
                where: { userid: "user-1" },
            });
            expect(result.profile).toEqual(updated);
        });

        it("issues two lookups when both user and trigger='update' are present", async () => {
            const initial = PROFILE_ROW;
            const refreshed = { ...PROFILE_ROW, zipCode: "10001" };
            mockFindUnique
                .mockResolvedValueOnce(initial)
                .mockResolvedValueOnce(refreshed);
            const token: any = {};
            const user: any = { id: "user-1" };

            const result = await capturedConfig.value.callbacks.jwt({
                token,
                user,
                trigger: "update",
            });

            expect(mockFindUnique).toHaveBeenCalledTimes(2);
            expect(result.sub).toBe("user-1");
            expect(result.profile).toEqual(refreshed);
        });

        it("does not overwrite token.profile on update when prisma returns null", async () => {
            mockFindUnique.mockResolvedValueOnce(null);
            const token: any = { sub: "user-1", profile: PROFILE_ROW };

            const result = await capturedConfig.value.callbacks.jwt({
                token,
                trigger: "update",
            });

            expect(result.profile).toEqual(PROFILE_ROW);
        });

        it("returns the token unchanged when no user and no update trigger", async () => {
            const token: any = { sub: "user-1", profile: PROFILE_ROW };

            const result = await capturedConfig.value.callbacks.jwt({
                token,
            });

            expect(mockFindUnique).not.toHaveBeenCalled();
            expect(result).toBe(token);
        });
    });

    describe("events.createUser", () => {
        it("creates a UserProfile row with the default shape for the new user", async () => {
            mockUserProfileCreate.mockResolvedValueOnce({ id: "profile-1" });

            await capturedConfig.value.events.createUser({
                user: { id: "user-1", email: "new@example.com" },
            });

            expect(mockUserProfileCreate).toHaveBeenCalledTimes(1);
            expect(mockUserProfileCreate).toHaveBeenCalledWith({
                data: {
                    userid: "user-1",
                    role: "user",
                    emailShowNotifications: false,
                    pushShowNotifications: false,
                },
            });
        });

        it("swallows errors from db.userProfile.create and logs instead of throwing", async () => {
            const consoleSpy = vi
                .spyOn(console, "error")
                .mockImplementation(() => {});
            mockUserProfileCreate.mockRejectedValueOnce(
                new Error("unique constraint failed"),
            );

            await expect(
                capturedConfig.value.events.createUser({
                    user: { id: "user-1" },
                }),
            ).resolves.toBeUndefined();

            expect(consoleSpy).toHaveBeenCalledWith(
                "Error creating user profile:",
                expect.any(Error),
            );
            consoleSpy.mockRestore();
        });
    });

    describe("sendVerificationRequest", () => {
        const findEmailProvider = () =>
            (capturedConfig.value.providers as Array<any>).find(
                (p) => p.id === "email",
            );

        it("calls createTransport with provider.server and sendMail with the rendered email", async () => {
            const sendMail = vi.fn().mockResolvedValue({
                rejected: [],
                pending: [],
            });
            mockCreateTransport.mockReturnValueOnce({ sendMail });
            mockBuildMagicLinkEmail.mockReturnValueOnce({
                subject: "Sign in to LaughTrack",
                text: "text body",
                html: "<p>html body</p>",
            });
            const provider = findEmailProvider();

            await provider.sendVerificationRequest({
                identifier: "user@example.com",
                url: "https://laugh-track.com/verify?token=abc",
                provider,
            });

            expect(mockCreateTransport).toHaveBeenCalledWith(provider.server);
            expect(mockBuildMagicLinkEmail).toHaveBeenCalledWith({
                url: "https://laugh-track.com/verify?token=abc",
            });
            expect(sendMail).toHaveBeenCalledWith({
                to: "user@example.com",
                from: provider.from,
                subject: "Sign in to LaughTrack",
                text: "text body",
                html: "<p>html body</p>",
            });
        });

        it("throws when sendMail returns rejected addresses", async () => {
            const sendMail = vi.fn().mockResolvedValue({
                rejected: ["bad@example.com"],
                pending: [],
            });
            mockCreateTransport.mockReturnValueOnce({ sendMail });
            mockBuildMagicLinkEmail.mockReturnValueOnce({
                subject: "s",
                text: "t",
                html: "h",
            });
            const provider = findEmailProvider();

            await expect(
                provider.sendVerificationRequest({
                    identifier: "bad@example.com",
                    url: "https://laugh-track.com/verify?token=abc",
                    provider,
                }),
            ).rejects.toThrow(
                "Email (bad@example.com) could not be sent",
            );
        });

        it("throws when sendMail returns pending addresses", async () => {
            const sendMail = vi.fn().mockResolvedValue({
                rejected: [],
                pending: ["pending@example.com"],
            });
            mockCreateTransport.mockReturnValueOnce({ sendMail });
            mockBuildMagicLinkEmail.mockReturnValueOnce({
                subject: "s",
                text: "t",
                html: "h",
            });
            const provider = findEmailProvider();

            await expect(
                provider.sendVerificationRequest({
                    identifier: "pending@example.com",
                    url: "https://laugh-track.com/verify?token=abc",
                    provider,
                }),
            ).rejects.toThrow(
                "Email (pending@example.com) could not be sent",
            );
        });
    });
});
