interface SearchDetailHeaderProps {
    title: string;
    subTitle: string;
}

const SearchDetailHeader = ({ title, subTitle }: SearchDetailHeaderProps) => {
    return (
        <div className="text-center py-8 bg-ivory">
            <h1 className="text-3xl font-bold text-[#2D1810] mb-2">{title}</h1>
            <p className="text-gray-600">{subTitle}</p>
        </div>
    );
};

export default SearchDetailHeader;
