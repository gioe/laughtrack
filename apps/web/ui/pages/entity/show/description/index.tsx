import { stripHtmlTags } from "@/util/primatives/stringUtil";

interface ShowDescriptionProps {
    description?: string | null;
}

const ShowDescription: React.FC<ShowDescriptionProps> = ({ description }) => {
    if (!description || !description.trim()) return null;

    const cleanDescription = stripHtmlTags(description);
    if (!cleanDescription) return null;

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-4 mb-6">
            <h2 className="font-gilroy-bold text-h3 font-bold text-foreground mb-3">
                About this show
            </h2>
            <p className="text-base text-gray-700 font-dmSans whitespace-pre-line leading-relaxed">
                {cleanDescription}
            </p>
        </section>
    );
};

export default ShowDescription;
