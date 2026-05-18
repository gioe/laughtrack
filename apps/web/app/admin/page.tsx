import { Button } from "@/ui/components/ui/button";
import { Building2 } from "lucide-react";
import Link from "next/link";

export default function AdminPage() {
    return (
        <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
            <div className="space-y-5">
                <p className="font-dmSans text-caption font-semibold uppercase text-copper">
                    Portal
                </p>
                <h1 className="font-chivo text-h1 leading-tight text-cedar">
                    Manage the LaughTrack catalog without leaving the product
                    system.
                </h1>
                <p className="max-w-2xl font-dmSans text-lead text-soft-charcoal">
                    Use this space for operational tools that need the same
                    comedy-first context, spacing, and navigation as the public
                    experience.
                </p>
            </div>
            <div className="rounded-lg border border-copper/20 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-copper/10 text-copper">
                        <Building2 className="h-5 w-5" />
                    </div>
                    <div>
                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                            Club operations
                        </h2>
                        <p className="font-dmSans text-caption text-soft-charcoal">
                            Review and edit club descriptions and hours.
                        </p>
                    </div>
                </div>
                <Button asChild variant="roundedShimmer">
                    <Link href="/admin/clubs">Open clubs</Link>
                </Button>
            </div>
        </section>
    );
}
