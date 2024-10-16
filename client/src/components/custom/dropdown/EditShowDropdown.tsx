'use client';

import useAddComedianModal from "@/hooks/useAddComedianModal";
import useAddShowTagModal from "@/hooks/useAddShowTagModal";
import {Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button} from "@nextui-org/react";

export const EditShowDropdown = () => {

  const showTagModal = useAddShowTagModal();
  const addComedianModal = useAddComedianModal();

  const addShowTag = () => {
    showTagModal.onOpen();
  }

  const addComedian = () => {
    addComedianModal.onOpen();
  }

  const items = [
    {
      key: "tag",
      label: "Add Tag",
    },
    {
      key: "comedian",
      label: "Add Comedian",
    },
  ];

  const handleClick = (key: string) => {
    if (key == 'tag') {
      addShowTag();
    }
    if (key == 'comedian') {
      addComedian();
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