import { create } from 'zustand'

interface AddShowTagModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useAddShowTagModal = create<AddShowTagModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useAddShowTagModal;