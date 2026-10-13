import { redirect } from "next/navigation";
export default async function EventReviewsPage({
    searchParams,
}: {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
    const input = await searchParams;
    const params = new URLSearchParams({
        workflow: "event_eligibility",
        status: "all",
    });
    for (const key of [
        "q",
        "source",
        "mode",
        "status",
        "after",
        "ceiling",
        "id",
    ]) {
        const value = input[key];
        if (typeof value === "string") params.set(key, value);
    }
    redirect(`/admin/reviews?${params}`);
}
