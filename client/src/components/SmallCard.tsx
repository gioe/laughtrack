import Image from "next/image"
import Link from "next/link";

interface SmallCardProps {
    name: string;
    filePath: string;
    url: string;
}

export const SmallCard: React.FC<SmallCardProps> = (
    { name, url, filePath}
) => {
    return (
        <Link
        href={{
            pathname: url,
        }}
    >
        <div className="flex items-center m-2 mt-5 space-x-4 rounded-xl 
        cursor-pointer hover:bg-gray-100 hover:scale-105 transition 
        transform duration-200 ease-out">
                <div className="relative h-16 w-16">
                    <Image alt="Club"
                        src={`/images/clubs/${filePath}`}
                        fill
                        priority={false}
                        sizes="16vw"
                        style={{ objectFit: "cover" }}
                        className="rounded-2xl">
                    </Image>
                </div>

                <div>
                    <h2>{name}</h2>
                </div>
        </div>
        </Link>
    )
}

export default SmallCard;