'use client';

import useAddShowsModal from "@/hooks/useAddShowsModal";
import {Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button} from "@nextui-org/react";

export const EditClubDowndown = () => {

  const addShowsModal = useAddShowsModal();

  const addShow = () => {
    addShowsModal.onOpen();
  }

  const addComedian = () => {
    addShowsModal.onOpen();
  }

  const items = [
    {
      key: "show",
      label: "Add Show",
    }
  ];

  const handleClick = (key: string) => {
    if (key == 'show') {
      addShow();
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