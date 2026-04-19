import { X } from "lucide-react";
import { useRef } from "react";
import { useDialogKeyboard } from "@/hooks";

// components/ui/Modal.tsx
interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
}

export const Modal = ({ isOpen, onClose, title, children }: ModalProps) => {
    const dialogRef = useRef<HTMLDivElement>(null);
    useDialogKeyboard({ isOpen, onClose, containerRef: dialogRef });

    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50">
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                tabIndex={-1}
                className="w-[calc(100%-2rem)] max-w-md bg-coconut-cream rounded-lg p-4 sm:p-6 m-4 outline-none"
            >
                <div className="flex justify-between items-center mb-2">
                    <h2 className="text-h2 font-bold font-gilroy-bold text-gray-800">
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
