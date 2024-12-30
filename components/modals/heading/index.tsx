"use client";

interface HeadingProps {
    title: string;
    subtitle?: string;
}

const Heading: React.FC<HeadingProps> = ({ title, subtitle }) => {
    return (
        <div className={"text-center"}>
            <div className="text-2xl font-fjalla text-copper">{title}</div>
            <div className="font-light text-copper font-fjalla mt-2">
                {subtitle}
            </div>
        </div>
    );
};

export default Heading;
