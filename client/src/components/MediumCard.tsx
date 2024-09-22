import { BsBuildingFillCheck } from "react-icons/bs";

interface MediumCardProps {
    name: string;
    instagram: string;
    count: number;
}

export const MediumCard: React.FC<MediumCardProps> = (
    { name, instagram, count }
) => {
    return (
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <div className="relative h-80 w-80">
                <BsBuildingFillCheck className="fill rounded-lg"/>
            </div>

            <div>
                <h3 className="text-2xl mt-3">{`${count} upcoming shows`}</h3>
            </div>
        </div>
    )
}

export default MediumCard;