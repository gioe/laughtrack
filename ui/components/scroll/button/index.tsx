import { ChevronLeft, ChevronRight } from "lucide-react";

interface NavButtonProps {
    direction: string;
    onClick: () => void;
}

const NavButton = ({ direction, onClick }: NavButtonProps) => {
    return (
        <button
            onClick={onClick}
            className="bg-copper rounded-full p-2 text-white hover:opacity-90 transition-opacity"
            aria-label={`Scroll ${direction}`}
        >
            {direction === "left" ? (
                <ChevronLeft size={24} />
            ) : (
                <ChevronRight size={24} />
            )}
        </button>
    );
};

export default NavButton;
