import { X } from "lucide-react";
import { useEffect, useState } from "react";

const FullScreenModal = ({ isOpen, onClose, children }) => {
    const [isAnimating, setIsAnimating] = useState(false);
    const [shouldRender, setShouldRender] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setShouldRender(true);
            setIsAnimating(true);
            // Save the current scroll position
            const scrollPosition = window.scrollY;
            // Add styles to prevent scrolling and maintain position
            document.body.style.position = "fixed";
            document.body.style.top = `-${scrollPosition}px`;
            document.body.style.width = "100%";
        } else {
            setIsAnimating(false);
            // Wait for animation to complete before unmounting
            const timer = setTimeout(() => setShouldRender(false), 300);
            // Restore scrolling and position when modal closes
            const scrollPosition = document.body.style.top;
            document.body.style.position = "";
            document.body.style.top = "";
            document.body.style.width = "";
            window.scrollTo(0, parseInt(scrollPosition || "0", 10) * -1);
            return () => clearTimeout(timer);
        }

        // Cleanup function to restore scrolling if component unmounts
        return () => {
            document.body.style.position = "";
            document.body.style.top = "";
            document.body.style.width = "";
        };
    }, [isOpen]);

    if (!shouldRender) return null;

    // Prevent clicks inside the modal from closing it
    const handleModalClick = (e) => {
        e.stopPropagation();
    };

    return (
        <div
            className={`fixed inset-0 z-50 flex items-center justify-center bg-black transition-all duration-300 ease-in-out
                ${isAnimating ? "bg-opacity-50" : "bg-opacity-0"}`}
            onClick={onClose}
        >
            <div
                className={`relative w-full h-full bg-white overflow-y-auto transform transition-transform duration-300 ease-in-out
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
