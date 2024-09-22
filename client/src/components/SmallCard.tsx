import { BsBuildingFillCheck } from "react-icons/bs";

interface SmallCardProps {
    name: string;
    url: string;
    count: number;
}

export const SmallCard: React.FC<SmallCardProps> = (
    { name, url, count }
) => {
    return (
        <div className="flex items-center m-2 mt-5 space-x-4 rounded-xl cursor-pointer hover:bg-gray-100 hover:scale-105 tranition transform duration-200 ease-out">
            <div className="relative h-16 w-16">
                <BsBuildingFillCheck className="fill rounded-lg"/>
            </div>

            <div>
                <h2>{name}</h2>
                <h3 className="text-gray-500">{`${count} upcoming shows`}</h3>
            </div>
        </div>
    )
}

export default SmallCard;