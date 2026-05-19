"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { AdminUserListItem } from "@/lib/admin/users";
import {
    AdminPagination,
    AdminSearchField,
    AdminSelectField,
    AdminToolbar,
    clampAdminPage,
} from "@/ui/pages/admin/shared/AdminControls";

type RoleFilter = "all" | "admin" | "user" | "missing-profile";
type UserSort = "created-desc" | "created-asc" | "name-asc" | "email-asc";

const ROLE_FILTER_OPTIONS: Array<{ value: RoleFilter; label: string }> = [
    { value: "all", label: "All users" },
    { value: "admin", label: "Admins" },
    { value: "user", label: "Users" },
    { value: "missing-profile", label: "Missing profile" },
];

const SORT_OPTIONS: Array<{ value: UserSort; label: string }> = [
    { value: "created-desc", label: "Newest accounts" },
    { value: "created-asc", label: "Oldest accounts" },
    { value: "name-asc", label: "Name A-Z" },
    { value: "email-asc", label: "Email A-Z" },
];

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

function matchesRoleFilter(user: AdminUserListItem, roleFilter: RoleFilter) {
    if (roleFilter === "all") return true;
    if (roleFilter === "missing-profile") return !user.profile;
    return user.profile?.role === roleFilter;
}

function getSearchText(user: AdminUserListItem) {
    return [
        user.name,
        user.email,
        user.id,
        user.profile?.id,
        user.profile?.role,
        user.profile?.zipCode,
        ...user.accountProviders,
        ...(user.profile?.favoriteComedians.map((comedian) => comedian.name) ??
            []),
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
}

function sortUsers(users: AdminUserListItem[], sort: UserSort) {
    return [...users].sort((a, b) => {
        if (sort === "created-desc") {
            return (
                new Date(b.createdAt).getTime() -
                    new Date(a.createdAt).getTime() ||
                a.email.localeCompare(b.email)
            );
        }
        if (sort === "created-asc") {
            return (
                new Date(a.createdAt).getTime() -
                    new Date(b.createdAt).getTime() ||
                a.email.localeCompare(b.email)
            );
        }
        if (sort === "name-asc") {
            return (a.name ?? a.email).localeCompare(b.name ?? b.email);
        }
        return a.email.localeCompare(b.email);
    });
}

export default function AdminUsersManager({
    users,
}: {
    users: AdminUserListItem[];
}) {
    const [query, setQuery] = useState("");
    const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
    const [sort, setSort] = useState<UserSort>("created-desc");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);

    const filteredUsers = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        return sortUsers(
            users.filter((user) => {
                if (!matchesRoleFilter(user, roleFilter)) return false;
                if (!normalizedQuery) return true;
                return getSearchText(user).includes(normalizedQuery);
            }),
            sort,
        );
    }, [query, roleFilter, sort, users]);

    const totalPages = Math.max(1, Math.ceil(filteredUsers.length / pageSize));
    const currentPage = clampAdminPage(page, totalPages);
    const pagedUsers = filteredUsers.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
    );

    function updateQuery(value: string) {
        setQuery(value);
        setPage(1);
    }

    function updateRoleFilter(value: RoleFilter) {
        setRoleFilter(value);
        setPage(1);
    }

    function updateSort(value: UserSort) {
        setSort(value);
        setPage(1);
    }

    function updatePageSize(value: number) {
        setPageSize(value);
        setPage(1);
    }

    return (
        <section className="space-y-3">
            <AdminToolbar>
                <AdminSearchField
                    label="Search users"
                    value={query}
                    placeholder="Search name, email, ID, provider, or favorite comedian"
                    onChange={updateQuery}
                />
                <div className="grid gap-3 sm:grid-cols-2">
                    <AdminSelectField
                        label="Role"
                        value={roleFilter}
                        options={ROLE_FILTER_OPTIONS}
                        onChange={updateRoleFilter}
                    />
                    <AdminSelectField
                        label="Sort"
                        value={sort}
                        options={SORT_OPTIONS}
                        onChange={updateSort}
                    />
                </div>
            </AdminToolbar>

            <AdminPagination
                page={currentPage}
                pageSize={pageSize}
                totalItems={filteredUsers.length}
                label="users"
                onPageChange={setPage}
                onPageSizeChange={updatePageSize}
            />

            <div className="overflow-hidden rounded-md border border-copper/20 bg-white">
                <div className="border-b border-copper/15 bg-cedar px-4 py-3">
                    <h2 className="font-gilroy-bold text-h3 text-coconut-cream">
                        Users
                    </h2>
                </div>

                {pagedUsers.length === 0 ? (
                    <p className="p-4 font-dmSans text-body text-soft-charcoal">
                        No user accounts found.
                    </p>
                ) : (
                    <ul className="divide-y divide-copper/15">
                        {pagedUsers.map((user) => {
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
            </div>

            <AdminPagination
                page={currentPage}
                pageSize={pageSize}
                totalItems={filteredUsers.length}
                label="users"
                onPageChange={setPage}
                onPageSizeChange={updatePageSize}
            />
        </section>
    );
}
