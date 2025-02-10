import { getLocalCdnUrl } from "@/util/cdnUtil";

export default function AuthImageContent() {
    return (
        <div className="w-1/2 relative bg-gray-900">
            <img
                src={getLocalCdnUrl(`sidebar.png`)}
                alt="Comedy show"
                className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black bg-opacity-40 flex flex-col justify-end p-8 text-white text-center font-inter text-[28px]">
                <h2 className="text-3xl font-bold mb-4">Laugh Local</h2>

                <p className="text-[14px] opacity-80 font-dmSans">
                    Laughtrack wants to get you out of the house. Find funny
                    shows. Follow funny comedians. Get informed when funny
                    comedians put on funny shows. Turn off that podcast and go
                    see the real thing.
                </p>
            </div>
        </div>
    );
}
