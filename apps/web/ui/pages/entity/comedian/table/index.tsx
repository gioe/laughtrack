import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowTable from "@/ui/pages/search/table";

interface TableWithHeaderProps {
    shows: ShowDTO[];
    total: number;
    children: React.ReactNode;
    errorMessage?: string;
}

const TableWithHeader: React.FC<TableWithHeaderProps> = ({
    shows,
    total,
    children,
    errorMessage,
}) => {
    return (
        <div className="flex-1">
            <h1 className="font-gilroy-bold text-h2 font-bold">
                Upcoming Shows
            </h1>
            <p className="text-gray-600 font-dmSans text-body mb-8">
                {total} upcoming shows
            </p>
            {children}
            <ShowTable shows={shows} errorMessage={errorMessage} />
        </div>
    );
};

export default TableWithHeader;
