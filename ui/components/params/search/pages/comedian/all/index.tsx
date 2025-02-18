"use client";

import TextInputComponent from "../../../components/textInput";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { QueryProperty, StyleContextKey } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../../components/container";

export default function ComedianSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const comedian = getTypedParam(QueryProperty.Comedian);

    const state = {
        comedian,
    };

    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);

    return (
        <SearchBarContainer maxWidth="max-w-xl">
            <TextInputComponent
                icon={
                    <Users className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
                }
                placeholder="Search for a comedian"
                value={state.comedian ?? ""}
                onChange={handleComedianSearch}
            />
        </SearchBarContainer>
    );
}
