import { X } from "lucide-react";

// components/ui/Modal.tsx
interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
}

export const Modal = ({ isOpen, onClose, title, children }: ModalProps) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="w-[calc(100%-2rem)] max-w-md bg-coconut-cream rounded-lg p-4 sm:p-6 m-4">
                <div className="flex justify-between items-center mb-2">
                    <h2 className="text-[26px] font-bold font-gilroy-bold text-gray-800">
                        {title}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <X size={20} />
                    </button>
                </div>
                {children}
            </div>
        </div>
    );
};
