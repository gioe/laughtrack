import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowTable from "@/ui/pages/search/table";

interface TableWithHeaderProps {
    shows: ShowDTO[];
    total: number;
    children: React.ReactNode;
}

const TableWithHeader: React.FC<TableWithHeaderProps> = ({
    shows,
    total,
    children,
}) => {
    return (
        <div className="flex-1">
            <h1 className="font-gilroy-bold text-[26px] font-bold">
                Upcoming Shows
            </h1>
            <p className="text-gray-600 font-dmSans text-[16px] mb-8">
                {total} upcoming shows
            </p>
            {children}
            <ShowTable shows={shows} />
        </div>
    );
};

export default TableWithHeader;
