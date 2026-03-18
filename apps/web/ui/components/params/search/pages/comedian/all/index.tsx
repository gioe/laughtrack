"use client";

import TextInputComponent from "../../../components/textInput";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";

// Per-entity composers remain separate: each has a distinct filter set
// (show: location + calendar + comedian + club; club: location + club; comedian: name only).
// The structural wrapper is already extracted as SearchBarLayout/SearchBarSection.
// A shared HOC would add indirection without reducing the per-entity JSX sections.
export default function ComedianSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const state = {
        comedian: getTypedParam(QueryProperty.Comedian),
    };

    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);
    return (
        <SearchBarLayout maxWidth="max-w-4xl">
            <SearchBarSection first last>
                <TextInputComponent
                    icon={
                        <Users
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for a comedian"
                    value={state.comedian ?? ""}
                    onChange={handleComedianSearch}
                />
            </SearchBarSection>
        </SearchBarLayout>
    );
}
