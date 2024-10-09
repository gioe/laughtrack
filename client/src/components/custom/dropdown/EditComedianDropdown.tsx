import {Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button} from "@nextui-org/react";

interface EditComedianDropdownProps {
  handleEditSocialClick?: () => void;
}

export const EditComedianDropdown: React.FC<EditComedianDropdownProps> = (
  { handleEditSocialClick }
) => {
  const items = [
    {
      key: "show",
      label: "Add Show",
    },
    {
      key: "social",
      label: "Edit Social Data",
    },
  ];

  const handleClick = (key: string) => {
    if (key == 'social' && handleEditSocialClick) {
      handleEditSocialClick();
    }
  }

  return (
    <Dropdown>
      <DropdownTrigger>
        <Button 
          variant="bordered" 
          className="bg-white"
        >
          Open Menu
        </Button>
      </DropdownTrigger>
      <DropdownMenu aria-label="Dynamic Actions" items={items}>
        {(item) => (
          <DropdownItem
            key={item.key}
            color={item.key === "delete" ? "danger" : "default"}
            className={item.key === "delete" ? "text-danger" : ""}
            onClick={() => {
              handleClick(item.key)
            }}
          >
            {item.label}
          </DropdownItem>
        )}
      </DropdownMenu>
    </Dropdown>
  );
}