import { create } from 'zustand'

interface ClearShowsModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useClearShowsModal = create<ClearShowsModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useClearShowsModal;