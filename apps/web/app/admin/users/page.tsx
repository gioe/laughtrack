import { CalendarDays, Mail, ShieldCheck, Star, UserRound } from "lucide-react";
import Link from "next/link";
import { listAdminUsers } from "@/lib/admin/users";

export const dynamic = "force-dynamic";

function formatDateTime(value: string | null): string {
    if (!value) return "Not recorded";
    return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(new Date(value));
}

function boolLabel(value: boolean): string {
    return value ? "Yes" : "No";
}

function SummaryCard({
    label,
    value,
    icon: Icon,
}: {
    label: string;
    value: string;
    icon: typeof UserRound;
}) {
    return (
        <div className="rounded-md border border-copper/20 bg-white p-4">
            <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-copper/10 text-copper-dark">
                    <Icon className="h-5 w-5" />
                </span>
                <div>
                    <p className="font-dmSans text-caption font-semibold uppercase text-soft-charcoal">
                        {label}
                    </p>
                    <p className="font-gilroy-bold text-h3 text-cedar">
                        {value}
                    </p>
                </div>
            </div>
        </div>
    );
}

export default async function AdminUsersPage() {
    const data = await listAdminUsers();

    return (
        <div className="space-y-6">
            <div>
                <p className="font-dmSans text-caption font-semibold uppercase text-copper-dark">
                    Admin · Users
                </p>
                <h1 className="mt-1 font-chivo text-h1 text-cedar">
                    Account holders
                </h1>
                <p className="mt-2 max-w-3xl font-dmSans text-body text-soft-charcoal">
                    Users who have created accounts, their profile settings,
                    authentication providers, and favorite comedians.
                </p>
            </div>

            <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                <SummaryCard
                    label="Users"
                    value={data.totals.userCount.toLocaleString()}
                    icon={UserRound}
                />
                <SummaryCard
                    label="Profiles"
                    value={data.totals.profileCount.toLocaleString()}
                    icon={ShieldCheck}
                />
                <SummaryCard
                    label="Admins"
                    value={data.totals.adminCount.toLocaleString()}
                    icon={ShieldCheck}
                />
                <SummaryCard
                    label="Favorites"
                    value={data.totals.favoriteComedianCount.toLocaleString()}
                    icon={Star}
                />
                <SummaryCard
                    label="Email opt-ins"
                    value={data.totals.emailNotificationOptInCount.toLocaleString()}
                    icon={Mail}
                />
                <SummaryCard
                    label="Push opt-ins"
                    value={data.totals.pushNotificationOptInCount.toLocaleString()}
                    icon={CalendarDays}
                />
            </section>

            <section className="overflow-hidden rounded-md border border-copper/20 bg-white">
                <div className="border-b border-copper/15 bg-cedar px-4 py-3">
                    <h2 className="font-gilroy-bold text-h3 text-coconut-cream">
                        Users
                    </h2>
                </div>

                {data.users.length === 0 ? (
                    <p className="p-4 font-dmSans text-body text-soft-charcoal">
                        No user accounts found.
                    </p>
                ) : (
                    <ul className="divide-y divide-copper/15">
                        {data.users.map((user) => {
                            const favorites =
                                user.profile?.favoriteComedians ?? [];
                            return (
                                <li
                                    key={user.id}
                                    className="grid gap-5 px-4 py-5 xl:grid-cols-[minmax(260px,0.8fr)_minmax(260px,0.8fr)_minmax(320px,1fr)]"
                                >
                                    <div className="min-w-0">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h3 className="break-words font-gilroy-bold text-h3 text-cedar">
                                                {user.name ?? "Unnamed user"}
                                            </h3>
                                            <span className="rounded-md border border-copper/25 bg-ecru-white px-2 py-1 font-dmSans text-caption font-semibold text-copper-dark">
                                                {user.profile?.role ??
                                                    "no profile"}
                                            </span>
                                        </div>
                                        <a
                                            href={`mailto:${user.email}`}
                                            className="mt-1 block break-words font-dmSans text-body font-semibold text-copper-dark hover:underline"
                                        >
                                            {user.email}
                                        </a>
                                        <dl className="mt-3 grid gap-1 font-dmSans text-caption text-soft-charcoal">
                                            <div>
                                                <dt className="inline font-semibold text-cedar">
                                                    User ID:
                                                </dt>{" "}
                                                <dd className="inline break-all">
                                                    {user.id}
                                                </dd>
                                            </div>
                                            {user.profile && (
                                                <div>
                                                    <dt className="inline font-semibold text-cedar">
                                                        Profile ID:
                                                    </dt>{" "}
                                                    <dd className="inline break-all">
                                                        {user.profile.id}
                                                    </dd>
                                                </div>
                                            )}
                                            <div>
                                                <dt className="inline font-semibold text-cedar">
                                                    Image:
                                                </dt>{" "}
                                                <dd className="inline break-all">
                                                    {user.image ?? "None"}
                                                </dd>
                                            </div>
                                        </dl>
                                    </div>

                                    <dl className="grid content-start gap-2 font-dmSans text-body text-soft-charcoal">
                                        <div>
                                            <dt className="font-semibold text-cedar">
                                                Created
                                            </dt>
                                            <dd>
                                                {formatDateTime(user.createdAt)}
                                            </dd>
                                        </div>
                                        <div>
                                            <dt className="font-semibold text-cedar">
                                                Updated
                                            </dt>
                                            <dd>
                                                {formatDateTime(user.updatedAt)}
                                            </dd>
                                        </div>
                                        <div>
                                            <dt className="font-semibold text-cedar">
                                                Email verified
                                            </dt>
                                            <dd>
                                                {formatDateTime(
                                                    user.emailVerifiedAt,
                                                )}
                                            </dd>
                                        </div>
                                        <div>
                                            <dt className="font-semibold text-cedar">
                                                Auth providers
                                            </dt>
                                            <dd>
                                                {user.accountProviders.length >
                                                0
                                                    ? user.accountProviders.join(
                                                          ", ",
                                                      )
                                                    : "None recorded"}
                                            </dd>
                                        </div>
                                        <div>
                                            <dt className="font-semibold text-cedar">
                                                Account records
                                            </dt>
                                            <dd>
                                                {user.accountCount} accounts ·{" "}
                                                {user.refreshTokenCount} refresh
                                                tokens ·{" "}
                                                {user.sentNotificationCount}{" "}
                                                notifications sent
                                            </dd>
                                        </div>
                                    </dl>

                                    <div className="space-y-3">
                                        <dl className="grid gap-1 font-dmSans text-body text-soft-charcoal">
                                            <div>
                                                <dt className="inline font-semibold text-cedar">
                                                    Email show notifications:
                                                </dt>{" "}
                                                <dd className="inline">
                                                    {boolLabel(
                                                        user.profile
                                                            ?.emailShowNotifications ??
                                                            false,
                                                    )}
                                                </dd>
                                            </div>
                                            <div>
                                                <dt className="inline font-semibold text-cedar">
                                                    Push show notifications:
                                                </dt>{" "}
                                                <dd className="inline">
                                                    {boolLabel(
                                                        user.profile
                                                            ?.pushShowNotifications ??
                                                            false,
                                                    )}
                                                </dd>
                                            </div>
                                            <div>
                                                <dt className="inline font-semibold text-cedar">
                                                    Comedian onboarding:
                                                </dt>{" "}
                                                <dd className="inline">
                                                    {boolLabel(
                                                        user.profile
                                                            ?.comedianOnboardingCompleted ??
                                                            false,
                                                    )}
                                                </dd>
                                            </div>
                                            <div>
                                                <dt className="inline font-semibold text-cedar">
                                                    Location:
                                                </dt>{" "}
                                                <dd className="inline">
                                                    {user.profile?.zipCode ??
                                                        "No ZIP"}{" "}
                                                    ·{" "}
                                                    {user.profile
                                                        ?.nearbyDistanceMiles ??
                                                        "No"}{" "}
                                                    miles
                                                </dd>
                                            </div>
                                        </dl>

                                        <div>
                                            <h4 className="font-dmSans text-body font-semibold text-cedar">
                                                Favorite comedians (
                                                {favorites.length})
                                            </h4>
                                            {favorites.length === 0 ? (
                                                <p className="font-dmSans text-caption text-soft-charcoal">
                                                    No favorites saved.
                                                </p>
                                            ) : (
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {favorites.map(
                                                        (comedian) => (
                                                            <Link
                                                                key={
                                                                    comedian.uuid
                                                                }
                                                                href={`/comedian/${encodeURIComponent(comedian.name)}`}
                                                                className="rounded-md border border-copper/25 bg-ecru-white px-2 py-1 font-dmSans text-caption font-semibold text-copper-dark hover:border-copper hover:bg-coconut-cream"
                                                            >
                                                                {comedian.name}{" "}
                                                                ·{" "}
                                                                {comedian.totalShows.toLocaleString()}{" "}
                                                                shows
                                                            </Link>
                                                        ),
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </section>
        </div>
    );
}
