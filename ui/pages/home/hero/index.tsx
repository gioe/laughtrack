import { UserInterface } from "@/objects/class/user/user.interface";
import Navbar from "@/ui/components/navbar";
import BackgroundImage from "@/ui/components/background";
import ContentWrapper from "@/ui/components/wrapper";
import HeroContent from "@/ui/components/hero";
import { getCdnUrl } from "@/util/cdnUtil";

interface HeroComponentProps {
    user: UserInterface | null;
}

const HeroComponent = ({ user }: HeroComponentProps) => {
    return (
        <section className="relative w-full h-[776px]">
            <BackgroundImage
                imageUrl={getCdnUrl(`laughtrack-hero.png`)}
                alt={"Header background image"}
            />
            <ContentWrapper>
                <Navbar currentUser={user} />
                <HeroContent title="Laughtrack" subtitle="Get out and laugh" />
            </ContentWrapper>
        </section>
    );
};

export default HeroComponent;
