import { ModalState } from "../objects/interfaces/modalState.interface";
import { create } from "zustand";

const useSocialDataModal = create<ModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({ isOpen: true }),
    onClose: () => set({ isOpen: false }),
}));

export default useSocialDataModal;
