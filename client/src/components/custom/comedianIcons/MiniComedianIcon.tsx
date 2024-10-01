import { ComedianInterface } from "@/interfaces/comedian.interface";
import { LineupItemInterface } from "@/interfaces/show.interface";
import Image from "next/image"
import Link from "next/link";

interface MiniComedianIconProps {
    comedian: ComedianInterface | LineupItemInterface;
}

export const MiniComedianIcon: React.FC<MiniComedianIconProps> = (
    { comedian }
) => {
    return (
        <div className="flex flex-col bg-yellow-500 w-20">
        <Link
            href={`/comedian/${comedian.name}`}
        >
            <div className="cursor-pointer hover:scale-105 t
            ransform transition duration-300 ease-out text-center">
                <div className="relative h-20 w-20">
                    <Image alt="Comedian"
                        src={`/images/comedians/square/${comedian.name}.png`}
                        fill
                        priority={false}
                        style={{ objectFit: "cover" }}
                        className="rounded-2xl">
                    </Image>
                </div>

                <div>
                    <label className="md:text-sm text-xs text-gray-500 text-light font-semibold text-left">{comedian.name}</label>
                </div>
            </div>
        </Link>
        </div>

    )
}

export default MiniComedianIcon;