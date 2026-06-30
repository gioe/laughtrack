"use client";

import { useMemo } from "react";
import { QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import { getClubProgrammingFilterOptions } from "@/lib/club/programmingLabels";
import { FilterChip } from "@/ui/components/params/filter/chips";

function parseFilterSlugs(filters: string | undefined): string[] {
    return filters
        ? filters
              .split(",")
              .map((slug) => slug.trim())
              .filter(Boolean)
        : [];
}

export default function ClubProgrammingFilters() {
    const { getTypedParam, setTypedParam } = useUrlParams();
    const filtersParam = getTypedParam(QueryProperty.Filters) ?? "";
    const selectedSlugs = useMemo(
        () => parseFilterSlugs(filtersParam),
        [filtersParam],
    );
    const options = useMemo(
        () => getClubProgrammingFilterOptions(filtersParam),
        [filtersParam],
    );

    const updateFilter = (slug: string) => {
        const nextSlugs = selectedSlugs.includes(slug)
            ? selectedSlugs.filter((selectedSlug) => selectedSlug !== slug)
            : [...selectedSlugs, slug];
        setTypedParam(QueryProperty.Filters, nextSlugs.join(","));
    };

    return (
        <section className="mb-6 pt-2 animate-slideUp">
            <h3 className="text-lead font-bold font-urbanist-bold text-foreground mb-3 pb-3 border-b border-subtle">
                Programming
            </h3>
            <div className="flex flex-wrap gap-2">
                {options.map((option) => (
                    <FilterChip
                        key={option.slug}
                        option={option}
                        onClick={updateFilter}
                        isSelected={selectedSlugs.includes(option.slug)}
                    />
                ))}
            </div>
        </section>
    );
}
