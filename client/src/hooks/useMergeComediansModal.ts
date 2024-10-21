import { create } from 'zustand'

interface MergeComediansModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useMergeComediansModal = create<MergeComediansModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useMergeComediansModal;