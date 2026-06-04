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

type UserPatch = {
    name?: string | null;
    image?: string | null;
    role?: "admin" | "user";
    zipCode?: string | null;
    nearbyDistanceMiles?: number | null;
    emailShowNotifications?: boolean;
    pushShowNotifications?: boolean;
    comedianOnboardingCompleted?: boolean;
};

type Overrides = {
    name?: string | null;
    image?: string | null;
    role?: "admin" | "user";
    zipCode?: string | null;
    nearbyDistanceMiles?: number | null;
    emailShowNotifications?: boolean;
    pushShowNotifications?: boolean;
    comedianOnboardingCompleted?: boolean;
};

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
        ...user.pushTokens.flatMap((token) => [
            token.id,
            token.platform,
            token.tokenPreview,
            token.isActive ? "active push token" : "inactive push token",
        ]),
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
                        {pagedUsers.map((user) => (
                            <UserRow key={user.id} user={user} />
                        ))}
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

function UserRow({ user }: { user: AdminUserListItem }) {
    const [overrides, setOverrides] = useState<Overrides>({});
    const [savingField, setSavingField] = useState<keyof UserPatch | null>(
        null,
    );
    const [fieldError, setFieldError] = useState<{
        field: keyof UserPatch;
        message: string;
    } | null>(null);

    const currentName =
        "name" in overrides ? (overrides.name ?? null) : user.name;
    const currentImage =
        "image" in overrides ? (overrides.image ?? null) : user.image;
    const currentRole = overrides.role ?? user.profile?.role ?? "user";
    const currentZip =
        "zipCode" in overrides
            ? (overrides.zipCode ?? null)
            : (user.profile?.zipCode ?? null);
    const currentMiles =
        "nearbyDistanceMiles" in overrides
            ? (overrides.nearbyDistanceMiles ?? null)
            : (user.profile?.nearbyDistanceMiles ?? null);
    const currentEmailOptIn =
        overrides.emailShowNotifications ??
        user.profile?.emailShowNotifications ??
        false;
    const currentPushOptIn =
        overrides.pushShowNotifications ??
        user.profile?.pushShowNotifications ??
        false;
    const currentOnboardingDone =
        overrides.comedianOnboardingCompleted ??
        user.profile?.comedianOnboardingCompleted ??
        false;

    const favorites = user.profile?.favoriteComedians ?? [];
    const activePushTokenCount = user.pushTokens.filter(
        (token) => token.isActive,
    ).length;
    const hasProfile = Boolean(user.profile);

    async function saveField<K extends keyof UserPatch>(
        field: K,
        value: UserPatch[K],
    ) {
        setSavingField(field);
        setFieldError(null);
        try {
            const response = await fetch(
                `/api/admin/users/${encodeURIComponent(user.id)}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ [field]: value }),
                },
            );
            const body = await response.json().catch(() => ({}));
            if (!response.ok) {
                setFieldError({
                    field,
                    message:
                        typeof body.error === "string"
                            ? body.error
                            : "Save failed",
                });
                return;
            }
            setOverrides((prev) => ({ ...prev, [field]: value }));
        } catch {
            setFieldError({ field, message: "Save failed" });
        } finally {
            setSavingField(null);
        }
    }

    return (
        <li className="grid gap-5 px-4 py-5 xl:grid-cols-[minmax(260px,0.8fr)_minmax(260px,0.8fr)_minmax(360px,1fr)]">
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    <h3 className="break-words font-gilroy-bold text-h3 text-cedar">
                        {currentName ?? "Unnamed user"}
                    </h3>
                    <span className="rounded-md border border-copper/25 bg-ecru-white px-2 py-1 font-dmSans text-caption font-semibold text-copper-dark">
                        {user.profile?.role ?? "no profile"}
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
                        <dd className="inline break-all">{user.id}</dd>
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
                            {currentImage ?? "None"}
                        </dd>
                    </div>
                </dl>
            </div>

            <dl className="grid content-start gap-2 font-dmSans text-body text-soft-charcoal">
                <div>
                    <dt className="font-semibold text-cedar">Created</dt>
                    <dd>{formatDateTime(user.createdAt)}</dd>
                </div>
                <div>
                    <dt className="font-semibold text-cedar">Updated</dt>
                    <dd>{formatDateTime(user.updatedAt)}</dd>
                </div>
                <div>
                    <dt className="font-semibold text-cedar">Email verified</dt>
                    <dd>{formatDateTime(user.emailVerifiedAt)}</dd>
                </div>
                <div>
                    <dt className="font-semibold text-cedar">Auth providers</dt>
                    <dd>
                        {user.accountProviders.length > 0
                            ? user.accountProviders.join(", ")
                            : "None recorded"}
                    </dd>
                </div>
                <div>
                    <dt className="font-semibold text-cedar">
                        Account records
                    </dt>
                    <dd>
                        {user.accountCount} accounts · {user.refreshTokenCount}{" "}
                        refresh tokens · {user.sentNotificationCount}{" "}
                        notifications sent
                    </dd>
                </div>
            </dl>

            <div className="space-y-3">
                <div className="rounded-md border border-copper/20 bg-ecru-white p-3">
                    <h4 className="font-gilroy-bold text-body text-cedar">
                        Edit user
                    </h4>
                    {!hasProfile && (
                        <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                            Profile fields are unavailable for accounts without
                            a profile.
                        </p>
                    )}
                    <div className="mt-3 grid gap-3">
                        <TextField
                            label="Name"
                            initial={currentName ?? ""}
                            placeholder="Unnamed user"
                            saving={savingField === "name"}
                            error={
                                fieldError?.field === "name"
                                    ? fieldError.message
                                    : null
                            }
                            onCommit={(value) => {
                                const trimmed = value.trim();
                                const next = trimmed === "" ? null : trimmed;
                                if (next === (currentName ?? null)) return;
                                saveField("name", next);
                            }}
                        />
                        <TextField
                            label="Image URL"
                            initial={currentImage ?? ""}
                            placeholder="https://…"
                            type="url"
                            saving={savingField === "image"}
                            error={
                                fieldError?.field === "image"
                                    ? fieldError.message
                                    : null
                            }
                            onCommit={(value) => {
                                const trimmed = value.trim();
                                const next = trimmed === "" ? null : trimmed;
                                if (next === (currentImage ?? null)) return;
                                saveField("image", next);
                            }}
                        />
                        <SelectField
                            label="Account role"
                            value={currentRole}
                            disabled={!hasProfile}
                            saving={savingField === "role"}
                            error={
                                fieldError?.field === "role"
                                    ? fieldError.message
                                    : null
                            }
                            options={[
                                { value: "user", label: "user" },
                                { value: "admin", label: "admin" },
                            ]}
                            onChange={(value) => {
                                if (value === currentRole) return;
                                saveField("role", value as "admin" | "user");
                            }}
                        />
                        <TextField
                            label="ZIP code"
                            initial={currentZip ?? ""}
                            placeholder="00000"
                            inputMode="numeric"
                            maxLength={5}
                            disabled={!hasProfile}
                            saving={savingField === "zipCode"}
                            error={
                                fieldError?.field === "zipCode"
                                    ? fieldError.message
                                    : null
                            }
                            onCommit={(value) => {
                                const trimmed = value.trim();
                                const next = trimmed === "" ? null : trimmed;
                                if (next === (currentZip ?? null)) return;
                                saveField("zipCode", next);
                            }}
                        />
                        <TextField
                            label="Nearby distance (miles)"
                            initial={
                                currentMiles == null ? "" : String(currentMiles)
                            }
                            placeholder="25"
                            inputMode="numeric"
                            type="number"
                            min={1}
                            step={1}
                            disabled={!hasProfile}
                            saving={savingField === "nearbyDistanceMiles"}
                            error={
                                fieldError?.field === "nearbyDistanceMiles"
                                    ? fieldError.message
                                    : null
                            }
                            onCommit={(value) => {
                                const trimmed = value.trim();
                                const next =
                                    trimmed === "" ? null : Number(trimmed);
                                if (
                                    next === (currentMiles ?? null) ||
                                    (next !== null &&
                                        (!Number.isFinite(next) || next <= 0))
                                ) {
                                    if (
                                        next !== null &&
                                        (!Number.isFinite(next) || next <= 0)
                                    ) {
                                        setFieldError({
                                            field: "nearbyDistanceMiles",
                                            message:
                                                "Must be a positive whole number",
                                        });
                                    }
                                    return;
                                }
                                saveField("nearbyDistanceMiles", next);
                            }}
                        />
                        <CheckboxField
                            label="Email show notifications"
                            checked={currentEmailOptIn}
                            disabled={!hasProfile}
                            saving={savingField === "emailShowNotifications"}
                            error={
                                fieldError?.field === "emailShowNotifications"
                                    ? fieldError.message
                                    : null
                            }
                            onChange={(checked) =>
                                saveField("emailShowNotifications", checked)
                            }
                        />
                        <CheckboxField
                            label="Push show notifications"
                            checked={currentPushOptIn}
                            disabled={!hasProfile}
                            saving={savingField === "pushShowNotifications"}
                            error={
                                fieldError?.field === "pushShowNotifications"
                                    ? fieldError.message
                                    : null
                            }
                            onChange={(checked) =>
                                saveField("pushShowNotifications", checked)
                            }
                        />
                        <CheckboxField
                            label="Comedian onboarding completed"
                            checked={currentOnboardingDone}
                            disabled={!hasProfile}
                            saving={
                                savingField === "comedianOnboardingCompleted"
                            }
                            error={
                                fieldError?.field ===
                                "comedianOnboardingCompleted"
                                    ? fieldError.message
                                    : null
                            }
                            onChange={(checked) =>
                                saveField(
                                    "comedianOnboardingCompleted",
                                    checked,
                                )
                            }
                        />
                    </div>
                </div>

                <details className="rounded-md border border-copper/20 bg-ecru-white p-3">
                    <summary className="cursor-pointer font-dmSans text-body font-semibold text-cedar">
                        Push tokens: {activePushTokenCount} active of{" "}
                        {user.pushTokens.length}
                    </summary>
                    {user.pushTokens.length === 0 ? (
                        <p className="mt-2 font-dmSans text-caption text-soft-charcoal">
                            No device tokens registered.
                        </p>
                    ) : (
                        <div className="mt-3 grid gap-3">
                            {user.pushTokens.map((token) => (
                                <dl
                                    key={token.id}
                                    className="rounded-md border border-copper/15 bg-white p-3 font-dmSans text-caption text-soft-charcoal"
                                >
                                    <div>
                                        <dt className="inline font-semibold text-cedar">
                                            Token:
                                        </dt>{" "}
                                        <dd className="inline break-all">
                                            {token.tokenPreview}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt className="inline font-semibold text-cedar">
                                            Status:
                                        </dt>{" "}
                                        <dd className="inline">
                                            {token.isActive
                                                ? "Active"
                                                : "Inactive"}{" "}
                                            · {token.platform}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt className="inline font-semibold text-cedar">
                                            Last refreshed:
                                        </dt>{" "}
                                        <dd className="inline">
                                            {formatDateTime(
                                                token.lastRegisteredAt,
                                            )}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt className="inline font-semibold text-cedar">
                                            Registered:
                                        </dt>{" "}
                                        <dd className="inline">
                                            {formatDateTime(token.createdAt)}
                                        </dd>
                                    </div>
                                    {!token.isActive && (
                                        <div>
                                            <dt className="inline font-semibold text-cedar">
                                                Revoked:
                                            </dt>{" "}
                                            <dd className="inline">
                                                {formatDateTime(
                                                    token.revokedAt,
                                                )}
                                            </dd>
                                        </div>
                                    )}
                                </dl>
                            ))}
                        </div>
                    )}
                </details>

                <div>
                    <h4 className="font-dmSans text-body font-semibold text-cedar">
                        Favorite comedians ({favorites.length})
                    </h4>
                    {favorites.length === 0 ? (
                        <p className="font-dmSans text-caption text-soft-charcoal">
                            No favorites saved.
                        </p>
                    ) : (
                        <div className="mt-2 flex flex-wrap gap-2">
                            {favorites.map((comedian) => (
                                <Link
                                    key={comedian.uuid}
                                    href={`/comedian/${encodeURIComponent(comedian.name)}`}
                                    className="rounded-md border border-copper/25 bg-ecru-white px-2 py-1 font-dmSans text-caption font-semibold text-copper-dark hover:border-copper hover:bg-coconut-cream"
                                >
                                    {comedian.name} ·{" "}
                                    {comedian.totalShows.toLocaleString()} shows
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </li>
    );
}

function FieldLabel({
    label,
    saving,
    error,
}: {
    label: string;
    saving: boolean;
    error: string | null;
}) {
    return (
        <div className="flex items-baseline justify-between gap-2 font-dmSans text-caption font-semibold text-cedar">
            <span>{label}</span>
            {saving ? (
                <span className="font-normal text-soft-charcoal">Saving…</span>
            ) : error ? (
                <span className="font-normal text-red-700">{error}</span>
            ) : null}
        </div>
    );
}

function TextField({
    label,
    initial,
    placeholder,
    type = "text",
    inputMode,
    maxLength,
    min,
    step,
    disabled,
    saving,
    error,
    onCommit,
}: {
    label: string;
    initial: string;
    placeholder?: string;
    type?: "text" | "url" | "number";
    inputMode?: "numeric" | "text";
    maxLength?: number;
    min?: number;
    step?: number;
    disabled?: boolean;
    saving: boolean;
    error: string | null;
    onCommit: (value: string) => void;
}) {
    const [value, setValue] = useState(initial);
    // When the underlying user (or saved override) changes, resync.
    const [lastInitial, setLastInitial] = useState(initial);
    if (initial !== lastInitial) {
        setLastInitial(initial);
        setValue(initial);
    }
    return (
        <label className="grid gap-1">
            <FieldLabel label={label} saving={saving} error={error} />
            <input
                type={type}
                inputMode={inputMode}
                maxLength={maxLength}
                min={min}
                step={step}
                disabled={disabled || saving}
                placeholder={placeholder}
                value={value}
                onChange={(event) => setValue(event.target.value)}
                onBlur={() => onCommit(value)}
                onKeyDown={(event) => {
                    if (event.key === "Enter") {
                        event.preventDefault();
                        event.currentTarget.blur();
                    }
                }}
                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30 disabled:bg-coconut-cream/40 disabled:text-soft-charcoal"
            />
        </label>
    );
}

function SelectField({
    label,
    value,
    options,
    disabled,
    saving,
    error,
    onChange,
}: {
    label: string;
    value: string;
    options: Array<{ value: string; label: string }>;
    disabled?: boolean;
    saving: boolean;
    error: string | null;
    onChange: (value: string) => void;
}) {
    return (
        <label className="grid gap-1">
            <FieldLabel label={label} saving={saving} error={error} />
            <select
                value={value}
                disabled={disabled || saving}
                onChange={(event) => onChange(event.target.value)}
                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30 disabled:bg-coconut-cream/40 disabled:text-soft-charcoal"
            >
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
        </label>
    );
}

function CheckboxField({
    label,
    checked,
    disabled,
    saving,
    error,
    onChange,
}: {
    label: string;
    checked: boolean;
    disabled?: boolean;
    saving: boolean;
    error: string | null;
    onChange: (checked: boolean) => void;
}) {
    return (
        <div className="grid gap-1">
            <label className="flex items-center gap-2 font-dmSans text-body text-cedar">
                <input
                    type="checkbox"
                    checked={checked}
                    disabled={disabled || saving}
                    onChange={(event) => onChange(event.target.checked)}
                    className="h-4 w-4 rounded border-soft-charcoal/40 text-copper-dark focus:ring-copper/30"
                />
                <span className="font-semibold">{label}</span>
                {saving ? (
                    <span className="font-dmSans text-caption text-soft-charcoal">
                        Saving…
                    </span>
                ) : null}
            </label>
            {error ? (
                <p className="font-dmSans text-caption text-red-700">{error}</p>
            ) : null}
        </div>
    );
}
