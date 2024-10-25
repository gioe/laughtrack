import { create } from 'zustand'

interface AddClubTagModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useAddClubTagModal = create<AddClubTagModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useAddClubTagModal;