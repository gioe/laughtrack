import { ModalState } from "../interfaces/modalState.interface";
import { create } from "zustand";

const useAddComedianModal = create<ModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({ isOpen: true }),
    onClose: () => set({ isOpen: false }),
}));

export default useAddComedianModal;
