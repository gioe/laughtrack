import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubSearchCard from "../../cards/club/search";

interface ClubGridProps {
    clubs: ClubDTO[];
}
const ClubGrid = ({ clubs }: ClubGridProps) => {
    return (
        <div className="w-full">
            {clubs.length > 0 ? (
                <div className="grid grid-cols-1 m:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6 animate-fade-in">
                    {clubs.map((dto) => {
                        return <ClubSearchCard key={dto.name} club={dto} />;
                    })}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-12 px-4">
                    <h2 className="font-bold font-dmSans text-[48px] text-center text-cedar mb-4">
                        No results found
                    </h2>
                    <p className="text-gray-600 text-center text-lg font-dmSans">
                        Does that place even exist?
                    </p>
                </div>
            )}
        </div>
    );
};

export default ClubGrid;
