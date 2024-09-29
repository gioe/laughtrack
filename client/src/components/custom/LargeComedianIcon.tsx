import { ComedianInterface } from "@/interfaces/comedian.interface";
import Image from "next/image"
import Link from "next/link";

interface LargeComedianIconProps {
    comedian: ComedianInterface;
}

export const LargeComedianIcon: React.FC<LargeComedianIconProps> = (
    { comedian }
) => {
    return (
        <Link
        href={{
            pathname: `/comedian/${comedian.id}`,
        }}
    >
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <div className="relative h-80 w-80">
                <Image alt="Comedian"
                    src={`/images/comedians/${comedian.name}.png`}
                    fill
                    priority={false}
                    sizes="80vw"
                    style={{objectFit:"cover"}}
                    className="rounded-2xl">
                </Image>
            </div>

            <div>
                <h3 className="text-xl mt-3">{comedian.name}</h3>
            </div>
            </div>
        </Link>
    )
}

export default LargeComedianIcon;