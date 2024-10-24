import { create } from 'zustand'

interface RunScrapeModalState {
    isOpen: boolean;
    onOpen: ()  => void;
    onClose: () => void;
}

const useRunScrapeModal = create<RunScrapeModalState>((set) => ({
    isOpen: false,
    onOpen: () => set({isOpen : true}),
    onClose: () => set({isOpen : false})
}))

export default useRunScrapeModal;