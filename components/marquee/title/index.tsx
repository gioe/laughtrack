"use client";

interface MarqueeTitleProps {
    name: string;
}
const MarqueeTitle = ({ name }: MarqueeTitleProps) => {
    return (
        <div className="flex flex-col lg:flex-row gap-3">
            <h3
                className="font-bebas font-semibold
         text-copper text-3xl"
            >
                {`${name}`}
            </h3>
            <h3
                className="font-bebas font-semibold 
        text-pine-tree text-3xl"
            >
                Presents:
            </h3>
        </div>
    );
};

export default MarqueeTitle;
