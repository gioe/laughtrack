import { X } from "lucide-react";
import { useEffect, useRef, useState, ReactNode, MouseEvent } from "react";
import { useDialogKeyboard } from "@/hooks";

interface FullScreenModalProps {
    isOpen: boolean;
    onClose: () => void;
    children: ReactNode;
}

const FullScreenModal = ({
    isOpen,
    onClose,
    children,
}: FullScreenModalProps) => {
    const [isAnimating, setIsAnimating] = useState(false);
    const [shouldRender, setShouldRender] = useState(false);
    const savedScrollY = useRef(0);
    const dialogRef = useRef<HTMLDivElement>(null);

    // Tie the hook to `shouldRender` (not `isOpen`) so focus is restored when
    // the modal actually unmounts — not mid close-animation.
    useDialogKeyboard({
        isOpen: shouldRender,
        onClose,
        containerRef: dialogRef,
    });

    useEffect(() => {
        if (isOpen) {
            setShouldRender(true);
            setIsAnimating(true);
            savedScrollY.current = window.scrollY;
            document.body.style.position = "fixed";
            document.body.style.top = `-${savedScrollY.current}px`;
            document.body.style.width = "100%";
            return () => {
                document.body.style.position = "";
                document.body.style.top = "";
                document.body.style.width = "";
                window.scrollTo(0, savedScrollY.current);
            };
        } else {
            setIsAnimating(false);
            document.body.style.position = "";
            document.body.style.top = "";
            document.body.style.width = "";
            window.scrollTo(0, savedScrollY.current);
            const timer = setTimeout(() => setShouldRender(false), 300);
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    if (!shouldRender) return null;

    // Prevent clicks inside the modal from closing it
    const handleModalClick = (e: MouseEvent<HTMLDivElement>) => {
        e.stopPropagation();
    };

    return (
        <div
            className={`fixed inset-0 z-50 flex items-center justify-center bg-black transition-all duration-300 ease-in-out
                ${isAnimating ? "bg-opacity-50" : "bg-opacity-0"}`}
            onClick={onClose}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                tabIndex={-1}
                className={`relative w-full h-full bg-white overflow-y-auto transform transition-transform duration-300 ease-in-out outline-none
                    ${isAnimating ? "translate-y-0" : "translate-y-full"}`}
                onClick={handleModalClick}
            >
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 z-50 p-2 rounded-full bg-white hover:bg-gray-100
                        transition-all duration-200 hover:scale-110 hover:shadow-md active:scale-95"
                >
                    <X size={24} className="text-gray-600" />
                </button>
                <div
                    className={`transform transition-all duration-300 delay-150
                    ${isAnimating ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
                >
                    {children}
                </div>
            </div>
        </div>
    );
};

export default FullScreenModal;
