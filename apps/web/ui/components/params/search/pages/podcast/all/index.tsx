"use client";

import { Podcast } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useStyleContext } from "@/contexts/StyleProvider";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";
import TextInputComponent from "../../../components/textInput";

export default function PodcastSearchBar() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const query = searchParams.get("q") ?? "";

    const handlePodcastSearch = (value: string) => {
        const current = new URLSearchParams(searchParams.toString());
        const trimmed = value.trim();
        if (trimmed) {
            current.set("q", trimmed);
        } else {
            current.delete("q");
        }
        current.delete("page");
        const qs = current.toString();
        router.replace(qs ? `?${qs}` : "/podcasts");
    };

    return (
        <SearchBarLayout>
            <SearchBarSection first last>
                <TextInputComponent
                    icon={
                        <Podcast
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search podcasts or hosts"
                    value={query}
                    onChange={handlePodcastSearch}
                    className={styleConfig.inputTextColor}
                    ariaLabel="Search podcasts"
                />
            </SearchBarSection>
        </SearchBarLayout>
    );
}
