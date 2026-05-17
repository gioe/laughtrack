import type { Metadata } from "next";
import GlobalSearchClient from "@/ui/pages/search/global";

export const metadata: Metadata = {
    title: "Search LaughTrack",
    description: "Search shows, comedians, clubs, and podcasts on LaughTrack.",
    alternates: {
        canonical: "/search",
    },
};

export default function SearchPage() {
    return <GlobalSearchClient />;
}
