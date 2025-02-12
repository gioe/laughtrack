import { UserInterface } from "@/objects/class/user/user.interface";
import Navbar from "@/ui/components/navbar";
import BackgroundImage from "@/ui/components/background";
import ContentWrapper from "@/ui/components/wrapper";
import HeroContent from "@/ui/components/hero";
import { getCdnUrl } from "@/util/cdnUtil";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface HeroComponentProps {
    profile?: UserProfileInterface | null;
}

const HeroComponent = ({ profile }: HeroComponentProps) => {
    return (
        <section className="relative w-full h-[776px]">
            <BackgroundImage
                imageUrl={getCdnUrl(`laughtrack-hero.png`)}
                alt={"Header background image"}
            />
            <ContentWrapper>
                <Navbar currentUser={profile} />
                <HeroContent title="Laughtrack" subtitle="Get out and laugh" />
            </ContentWrapper>
        </section>
    );
};

export default HeroComponent;
