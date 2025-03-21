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
        <section className="relative w-full h-[500px] sm:h-[600px] md:h-[700px] lg:h-[776px]">
            <BackgroundImage
                imageUrl={getCdnUrl(`laughtrack-hero.png`)}
                alt={"Header background image"}
            />
            <ContentWrapper>
                <Navbar currentUser={profile} />
                <div className="flex flex-col items-center justify-center h-full text-center w-full px-4 sm:px-6">
                    <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-2 sm:mb-4 font-chivo text-white">
                        Laughtrack
                    </h1>
                    <p className="text-lg sm:text-xl text-gray-200 mb-8 sm:mb-12 max-w-3xl font-chivo">
                        Get out and laugh
                    </p>
                    <ShowSearchForm />
                </div>
            </ContentWrapper>
        </section>
    );
};

export default HeroComponent;
