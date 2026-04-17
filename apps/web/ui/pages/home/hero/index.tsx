import Navbar from "@/ui/components/navbar";
import BackgroundImage from "@/ui/components/background";
import ContentWrapper from "@/ui/components/wrapper";
import { getCdnUrl } from "@/util/cdnUtil";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import ShowSearchForm from "@/ui/components/params/search/pages/home";

interface HeroComponentProps {
    profile?: UserProfileInterface | null;
}

const HeroComponent = ({ profile }: HeroComponentProps) => {
    return (
        <section className="relative w-full h-[380px] sm:h-[600px] md:h-[700px] lg:h-[776px] overflow-hidden">
            <BackgroundImage
                imageUrl={getCdnUrl(`laughtrack-hero.png`)}
                alt={"Header background image"}
            />
            <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" />
            <ContentWrapper>
                <Navbar currentUser={profile} />
                <div className="flex flex-col items-center justify-center h-full text-center w-full px-4 sm:px-6 relative">
                    <div className="animate-fadeIn">
                        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold mb-4 sm:mb-6 font-chivo text-white drop-shadow-lg transform transition-transform duration-300 hover:scale-[1.02]">
                            Get out and laugh
                        </h1>
                        <p className="text-xl sm:text-2xl text-gray-100 mb-8 sm:mb-12 max-w-3xl font-chivo animate-slideUp opacity-90">
                            Find live comedy shows, clubs, and comedians near
                            you.
                        </p>
                        <div className="transform transition-all duration-300 hover:scale-[1.02]">
                            <ShowSearchForm />
                        </div>
                    </div>
                </div>
            </ContentWrapper>
        </section>
    );
};

export default HeroComponent;
