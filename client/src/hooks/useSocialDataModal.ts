import { create } from 'zustand'

interface SocialDataModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useSocialDataModal = create<SocialDataModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useSocialDataModal;