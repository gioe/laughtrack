import { create } from 'zustand'

interface AddComediansModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useAddComedianModal = create<AddComediansModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useAddComedianModal;