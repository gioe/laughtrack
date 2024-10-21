'use client';

import useAddShowsModal from "@/hooks/useAddShowsModal";
import useMergeComediansModal from "@/hooks/useMergeComediansModal";
import useSocialDataModal from "@/hooks/useSocialDataModal";
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button } from "@nextui-org/react";

export const EditComedianDropdown = () => {

  const socialDataModal = useSocialDataModal();
  
  const mergeComediansModal = useMergeComediansModal();

  const addShowsModal = useAddShowsModal();

  const items = [
    {
      key: "social",
      label: "Edit Social Data",
    }, {
      key: "merge",
      label: "Merge Comedians",
    },
    {
      key: "show",
      label: "Add Show",
    },
  ];

  const handleClick = (key: string) => {
    if (key == 'social') {
      socialDataModal.onOpen();
    } else if (key == 'merge') {
      console.log("OPEN MERGE COMDIANS MODAL")
      mergeComediansModal.onOpen();
    } else if (key == "social") {
      addShowsModal.onOpen();
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
            onClick={() => handleClick(item.key)}
          >
            {item.label}
          </DropdownItem>
        )}
      </DropdownMenu>
    </Dropdown>
  );
}