import { db } from "@/lib/db";

export type AdminUserListItem = {
    id: string;
    name: string | null;
    email: string;
    emailVerifiedAt: string | null;
    image: string | null;
    createdAt: string;
    updatedAt: string;
    accountProviders: string[];
    accountCount: number;
    refreshTokenCount: number;
    sentNotificationCount: number;
    profile: {
        id: string;
        role: string;
        emailShowNotifications: boolean;
        pushShowNotifications: boolean;
        comedianOnboardingCompleted: boolean;
        zipCode: string | null;
        nearbyDistanceMiles: number | null;
        favoriteComedians: Array<{
            id: number;
            uuid: string;
            name: string;
            popularity: number;
            totalShows: number;
        }>;
    } | null;
};

export type AdminUsersData = {
    users: AdminUserListItem[];
    totals: {
        userCount: number;
        profileCount: number;
        adminCount: number;
        favoriteComedianCount: number;
        emailNotificationOptInCount: number;
        pushNotificationOptInCount: number;
    };
};

function toIso(value: Date | null | undefined): string | null {
    return value ? value.toISOString() : null;
}

export async function listAdminUsers(): Promise<AdminUsersData> {
    const users = await db.user.findMany({
        select: {
            id: true,
            name: true,
            email: true,
            emailVerified: true,
            image: true,
            createdAt: true,
            updatedAt: true,
            accounts: {
                select: {
                    provider: true,
                },
                orderBy: [{ provider: "asc" }],
            },
            profile: {
                select: {
                    id: true,
                    role: true,
                    emailShowNotifications: true,
                    pushShowNotifications: true,
                    comedianOnboardingCompleted: true,
                    zipCode: true,
                    nearbyDistanceMiles: true,
                    favoriteComedians: {
                        select: {
                            comedian: {
                                select: {
                                    id: true,
                                    uuid: true,
                                    name: true,
                                    popularity: true,
                                    totalShows: true,
                                },
                            },
                        },
                        orderBy: {
                            comedian: {
                                name: "asc",
                            },
                        },
                    },
                },
            },
            _count: {
                select: {
                    accounts: true,
                    refreshTokens: true,
                    sentNotifications: true,
                },
            },
        },
        orderBy: [{ createdAt: "desc" }, { email: "asc" }],
    });

    const mappedUsers = users.map((user): AdminUserListItem => {
        const favoriteComedians =
            user.profile?.favoriteComedians.map(({ comedian }) => ({
                id: comedian.id,
                uuid: comedian.uuid,
                name: comedian.name,
                popularity: comedian.popularity,
                totalShows: comedian.totalShows,
            })) ?? [];

        return {
            id: user.id,
            name: user.name,
            email: user.email,
            emailVerifiedAt: toIso(user.emailVerified),
            image: user.image,
            createdAt: toIso(user.createdAt) ?? "",
            updatedAt: toIso(user.updatedAt) ?? "",
            accountProviders: Array.from(
                new Set(user.accounts.map((account) => account.provider)),
            ),
            accountCount: user._count.accounts,
            refreshTokenCount: user._count.refreshTokens,
            sentNotificationCount: user._count.sentNotifications,
            profile: user.profile
                ? {
                      id: user.profile.id,
                      role: user.profile.role,
                      emailShowNotifications:
                          user.profile.emailShowNotifications,
                      pushShowNotifications: user.profile.pushShowNotifications,
                      comedianOnboardingCompleted:
                          user.profile.comedianOnboardingCompleted,
                      zipCode: user.profile.zipCode,
                      nearbyDistanceMiles: user.profile.nearbyDistanceMiles,
                      favoriteComedians,
                  }
                : null,
        };
    });

    return {
        users: mappedUsers,
        totals: {
            userCount: mappedUsers.length,
            profileCount: mappedUsers.filter((user) => user.profile).length,
            adminCount: mappedUsers.filter(
                (user) => user.profile?.role === "admin",
            ).length,
            favoriteComedianCount: mappedUsers.reduce(
                (sum, user) =>
                    sum + (user.profile?.favoriteComedians.length ?? 0),
                0,
            ),
            emailNotificationOptInCount: mappedUsers.filter(
                (user) => user.profile?.emailShowNotifications,
            ).length,
            pushNotificationOptInCount: mappedUsers.filter(
                (user) => user.profile?.pushShowNotifications,
            ).length,
        },
    };
}
