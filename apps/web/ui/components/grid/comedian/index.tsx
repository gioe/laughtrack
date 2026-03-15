import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";

interface ComedianGridProps {
    comedians: ComedianDTO[];
    className: string;
    isTrending?: boolean;
}
const ComedianGrid = ({
    comedians,
    className,
    isTrending,
}: ComedianGridProps) => {
    return (
        <div className="w-full">
            {comedians.length > 0 ? (
                <div className={`${className} animate-fade-in`}>
                    {comedians.map((dto) => (
                        <ComedianGridCard
                            key={dto.name}
                            entity={dto}
                            isTrending={isTrending}
                        />
                    ))}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-12 px-4">
                    <h2 className="font-bold font-dmSans text-[48px] text-center text-cedar mb-4">
                        No results found
                    </h2>
                    <p className="text-gray-600 text-center text-lg font-dmSans">
                        That person must not be funny enough.
                    </p>
                </div>
            )}
        </div>
    );
};

export default ComedianGrid;
