"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowTable from "@/ui/pages/search/table";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ShowSearchClientProps {
    data: ShowDTO[];
    total: number;
    zipCapTriggered?: boolean;
}

const ShowSearchClient = ({
    data,
    total,
    zipCapTriggered,
}: ShowSearchClientProps) => {
    const searchParams = useSearchParams();
    const zip = searchParams.get("zip") ?? undefined;

    const broadenHref = (() => {
        if (!zip) return null;
        const next = new URLSearchParams(searchParams.toString());
        next.delete("zip");
        next.delete("distance");
        next.delete("page");
        const qs = next.toString();
        return qs ? `/show/search?${qs}` : "/show/search";
    })();

    const emptyAction = broadenHref ? (
        <Link
            href={broadenHref}
            className="inline-block bg-cedar text-white font-dmSans font-semibold px-6 py-3 rounded-full hover:bg-copper transition-colors"
        >
            Browse all shows
        </Link>
    ) : undefined;

    return (
        <>
            {zipCapTriggered && (
                <p className="px-4 pt-2 text-sm text-amber-700">
                    Too many locations matched. Try a more specific search like{" "}
                    <strong>&quot;City, ST&quot;</strong> for better results.
                </p>
            )}
            <SearchClientShell total={total}>
                <ShowTable shows={data} emptyAction={emptyAction} />
            </SearchClientShell>
        </>
    );
};

export default ShowSearchClient;
