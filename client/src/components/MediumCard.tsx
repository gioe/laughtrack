import Image from "next/image"
import Link from "next/link";

interface MediumCardProps {
    name: string;
    instagram: string;
    count: number;
}

export const MediumCard: React.FC<MediumCardProps> = (
    { name, instagram, count }
) => {
    return (
        <Link
        href={{
            pathname: `https://instagram.com/${instagram}`,
        }}
    >
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <div className="relative h-80 w-80">
                <Image alt="Comedian"
                    src={`/images/comedians/${name}.png`}
                    fill
                    priority={false}
                    sizes="80vw"
                    style={{objectFit:"cover"}}
                    className="rounded-2xl">
                </Image>
            </div>

            <div>
                <h3 className="text-xl mt-3">{name}</h3>
            </div>
            </div>
        </Link>
    )
}

export default MediumCard;