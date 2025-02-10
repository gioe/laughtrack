interface SearchDetailHeaderProps {
    title: string;
    subTitle: string;
}

const SearchDetailHeader = ({ title, subTitle }: SearchDetailHeaderProps) => {
    return (
        <div className="text-center py-8 bg-ivory">
            <h1 className="text-[32px] font-bold text-cedar font-gilroy-bold mb-2">
                {title}
            </h1>
            <p className="text-gray-600 text-[16px] font-dmSans">{subTitle}</p>
        </div>
    );
};

export default SearchDetailHeader;
