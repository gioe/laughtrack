import { CalendarDays, Mail, ShieldCheck, Star, UserRound } from "lucide-react";
import { listAdminUsers } from "@/lib/admin/users";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
import AdminUsersManager from "@/ui/pages/admin/users/AdminUsersManager";

export const dynamic = "force-dynamic";

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
            <AdminPageHeader
                eyebrow="Admin · Users"
                title="Account holders"
                description="Users who have created accounts, their profile settings, authentication providers, and favorite comedians."
            />

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

            <AdminUsersManager users={data.users} />
        </div>
    );
}
