"use client";

interface HeadingProps {
    title: string;
    subtitle?: string;
}

const Heading: React.FC<HeadingProps> = ({ title, subtitle }) => {
    return (
        <div className={"text-center"}>
            <div className="text-2xl font-gilroy-bold font-bold text-copper">{title}</div>
            <div className="font-light text-copper font-dmSans mt-2">
                {subtitle}
            </div>
        </div>
    );
};

export default Heading;
