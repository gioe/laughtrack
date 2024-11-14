import { ModalState } from "../objects/interface/modalState.interface";
import { create } from "zustand";

const useMergeComediansModal = create<ModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({ isOpen: true }),
    onClose: () => set({ isOpen: false }),
}));

export default useMergeComediansModal;
