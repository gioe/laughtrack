import { create } from 'zustand'

interface AddShowsModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useAddShowsModal = create<AddShowsModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useAddShowsModal;