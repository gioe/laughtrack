import { X } from "lucide-react";

const FullScreenModal = ({ isOpen, onClose, children }) => {
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
                className="relative w-full h-full bg-white"
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
