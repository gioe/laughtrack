interface SearchDetailHeaderProps {
    title: string;
    subTitle: string;
}

const SearchDetailHeader = ({ title, subTitle }: SearchDetailHeaderProps) => {
    return (
        <div className="text-center py-6 md:py-8 bg-coconut-cream px-4">
            <h1 className="text-2xl sm:text-3xl md:text-[32px] font-bold text-cedar font-gilroy-bold mb-1 sm:mb-2">
                {title}
            </h1>
            <p className="text-sm sm:text-base md:text-[16px] font-dmSans text-gray-600">
                {subTitle}
            </p>
        </div>
    );
};

export default SearchDetailHeader;
