export interface ModalState {
  isOpen: boolean;
  onOpen: ()  => void;
  onClose: () => void;
}