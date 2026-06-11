"use client";

import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubGrid from "@/ui/components/grid/club";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ClubSearchClientProps {
    data: ClubDTO[];
    total: number;
}

const ClubSearchClient = ({ data, total }: ClubSearchClientProps) => {
    return (
        <SearchClientShell total={total}>
            <ClubGrid clubs={data} />
        </SearchClientShell>
    );
};

export default ClubSearchClient;
