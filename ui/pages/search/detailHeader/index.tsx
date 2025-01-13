interface DetailHeaderProps {
    title: string;
    subTitle: string;
}

const DetailHeader = ({ title, subTitle }: DetailHeaderProps) => {
    return (
        <div className="text-center py-8 bg-ivory">
            <h1 className="text-3xl font-bold text-[#2D1810] mb-2">{title}</h1>
            <p className="text-gray-600">{subTitle}</p>
        </div>
    );
};

export default DetailHeader;
