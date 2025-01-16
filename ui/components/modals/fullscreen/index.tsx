import { X } from "lucide-react";
import { useEffect } from "react";

const FullScreenModal = ({ isOpen, onClose, children }) => {
    useEffect(() => {
        if (isOpen) {
            // Save the current scroll position
            const scrollPosition = window.scrollY;
            // Add styles to prevent scrolling and maintain position
            document.body.style.position = "fixed";
            document.body.style.top = `-${scrollPosition}px`;
            document.body.style.width = "100%";
        } else {
            // Restore scrolling and position when modal closes
            const scrollPosition = document.body.style.top;
            document.body.style.position = "";
            document.body.style.top = "";
            document.body.style.width = "";
            window.scrollTo(0, parseInt(scrollPosition || "0", 10) * -1);
        }

        // Cleanup function to restore scrolling if component unmounts
        return () => {
            document.body.style.position = "";
            document.body.style.top = "";
            document.body.style.width = "";
        };
    }, [isOpen]);

    if (!isOpen) return null;

    // Prevent clicks inside the modal from closing it
    const handleModalClick = (e) => {
        e.stopPropagation();
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 transition-opacity"
            onClick={onClose}
        >
            <div
                className="relative w-full h-full bg-white overflow-y-auto"
                onClick={handleModalClick}
            >
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 z-50 p-2 rounded-full bg-white hover:bg-gray-100 transition-colors"
                >
                    <X size={24} className="text-gray-600" />
                </button>
                {children}
            </div>
        </div>
    );
};

export default FullScreenModal;
