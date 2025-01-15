import { SocialData } from "@/objects/class/socialData/SocialData";
import { Phone, Globe, Clock } from "lucide-react";
import NavButton from "./button";

interface ClubDataColumnProps {
    leftOnClick: () => void;
    rightOnClick: () => void;
}

const ScrollButtons = ({ leftOnClick, rightOnClick }: ClubDataColumnProps) => {
    return (
        <div className="flex gap-2">
            <NavButton direction="left" onClick={leftOnClick} />
            <NavButton direction="right" onClick={rightOnClick} />
        </div>
    );
};

export default ScrollButtons;
