import { UserInterface } from "@/objects/class/user/user.interface";
import Navbar from "@/ui/components/navbar";
import BackgroundImage from "@/ui/components/background";
import ContentWrapper from "@/ui/components/wrapper";
import HeroContent from "@/ui/components/hero";

export const getCdnImageUrl = (imagePath: string) => {
    return new URL(
        imagePath,
        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
    ).toString();
};

interface HeroComponentProps {
    user: UserInterface | null;
}

const HeroComponent = ({ user }: HeroComponentProps) => {
    return (
        <section className="relative w-full h-[776px]">
            <BackgroundImage
                imageUrl={getCdnImageUrl(`laughtrack-hero.png`)}
                alt={"Header background image"}
            />
            <ContentWrapper>
                <Navbar currentUser={user} />
                <HeroContent title="Laughtrack" subtitle="Have a laugh" />
            </ContentWrapper>
        </section>
    );
};

export default HeroComponent;
