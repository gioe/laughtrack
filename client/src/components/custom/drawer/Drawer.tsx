
interface SideDrawerProps {
    isOpen: boolean;
    onClose: () => void;
}

const Drawer: React.FC<SideDrawerProps> = ({ isOpen }) => {
  return (
    <div className={`drawer ${isOpen ? 'open' : ''}`}>
      <div className="drawer-content">
        {/* Your drawer content goes here */}
      </div>
    </div>
  );
};

export default Drawer;