import { create } from 'zustand'

interface AddComedianTagModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useAddComedianTagModal = create<AddComedianTagModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useAddComedianTagModal;