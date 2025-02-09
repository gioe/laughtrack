import ShowSearchForm from "../params/searchbar/home";

interface HeroContentProps {
    title: string;
    subtitle: string;
}

export default function HeroContent({ title, subtitle }: HeroContentProps) {
    return (
        <div className="flex flex-col items-center justify-center h-full text-center w-full">
            <h1 className="text-white text-6xl font-bold mb-4 font-chivo">
                {title}
            </h1>
            <p className="text-gray-200 text-xl mb-12 max-w-3xl font-chivo">
                {subtitle}
            </p>
            <ShowSearchForm />
        </div>
    );
}
