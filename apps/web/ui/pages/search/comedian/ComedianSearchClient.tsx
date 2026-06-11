"use client";

import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ComedianSearchClientProps {
    data: ComedianDTO[];
    total: number;
}

const ComedianSearchClient = ({ data, total }: ComedianSearchClientProps) => {
    return (
        <SearchClientShell total={total}>
            <ComedianGrid
                comedians={data}
                className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
            />
        </SearchClientShell>
    );
};

export default ComedianSearchClient;
