import Image from "next/image";
import { UserInterface } from "@/objects/class/user/user.interface";
import Navbar from "@/components/navbar";
import ShowSearchForm from "@/components/form/showSearch";

interface HeroComponentProps {
    user: UserInterface | null;
    cities: string;
}

const HeroComponent = ({ user, cities }) => {
    const imageUrl = new URL(
        `laughtrack-hero.png`,
        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
    );
    return (
        <section className="relative w-full h-[776px]">
            {/* Background Image Container */}
            <div className="absolute inset-0">
                {/* Remove max-width constraint for full-width background */}
                <div className="relative w-full h-full">
                    {/* Black overlay */}
                    <div className="absolute inset-0 bg-black/30 z-10" />
                    {/* Gradient overlay */}
                    <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-black/70 z-10" />
                    <Image
                        src={imageUrl.toString()}
                        alt="Comedy club background"
                        width={2880}
                        height={1772}
                        className="object-cover object-center w-full h-full"
                        priority
                        quality={90}
                    />
                </div>
            </div>
            {/* Content Container - centered with max-width */}
            <div className="relative h-full z-20">
                <Navbar currentUser={user} />
                <div className="max-w-7xl mx-auto h-full">
                    {/* Hero Content */}
                    <div className="flex flex-col items-center justify-center h-full text-center w-full">
                        <h1 className="text-white text-6xl font-bold mb-4">
                            Laughtrack
                        </h1>
                        <p className="text-gray-200 text-xl mb-12 max-w-3xl">
                            Laugh a little
                        </p>
                        <ShowSearchForm cities={JSON.stringify(cities)} />
                    </div>
                </div>
            </div>
        </section>
    );
};

export default HeroComponent;
