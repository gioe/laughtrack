import { Show } from "@/objects/class/show/Show";
import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";
import ShowTable from "@/ui/pages/search/table";

interface TableWithHeaderProps {
    shows: ShowDTO[];
    total: number;
}

const TableWithHeader: React.FC<TableWithHeaderProps> = ({ shows, total }) => {
    return (
        <div className="flex-1">
            <h1 className="text-2xl font-bold">Upcoming Shows</h1>
            <p className="text-gray-600 mb-8">{total} upcoming shows</p>
            <ShowTable shows={shows} />
        </div>
    );
};

export default TableWithHeader;
