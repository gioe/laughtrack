import Image from "next/image"
import Link from "next/link";

interface MiniCardProps {
    name: string;
    id: number;
}

export const MiniCard: React.FC<MiniCardProps> = (
    { name, id }
) => {
    return (
        <Link
        href={{
            pathname: `/`,
        }}
    >
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out text-center">
            <div className="relative h-20 w-20">
                <Image alt="Comedian"
                    src={`/images/comedians/${name}.png`}
                    fill
                    priority={false}
                    style={{objectFit:"cover"}}
                    className="rounded-2xl">
                </Image>
            </div>

            <div>
                <label className="md:text-sm text-xs text-gray-500 text-light font-semibold text-left">{name}</label>
            </div>
            </div>
        </Link>
    )
}

export default MiniCard;