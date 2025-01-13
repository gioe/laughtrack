import { Show } from "@/objects/class/show/Show";
import ShowCard from "@/ui/components/cards/show";

interface TableWithHeaderProps {
    entityString: string;
}

const TableWithHeader: React.FC<TableWithHeaderProps> = ({ entityString }) => {
    const shows = JSON.parse(entityString) as Show[];
    return (
        <div className="flex-1 pr-8">
            <h1 className="text-2xl font-bold mb-2">Upcoming Shows</h1>
            <p className="text-gray-600 mb-8">{shows.length} upcoming shows</p>
            {shows.map((show, index) => (
                <ShowCard key={index} show={show} />
            ))}
        </div>
    );
};

export default TableWithHeader;
