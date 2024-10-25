'use client';

import useAddComedianTagModal from "@/hooks/useAddComedianTagModal";
import useMergeComediansModal from "@/hooks/useMergeComediansModal";
import useSocialDataModal from "@/hooks/useSocialDataModal";
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button } from "@nextui-org/react";

export const EditComedianDropdown = () => {

  const socialDataModal = useSocialDataModal();
  const mergeComediansModal = useMergeComediansModal();
  const comedianTagModal = useAddComedianTagModal();

  const items = [
    {
      key: "social",
      label: "Edit Social Data",
    },
    {
      key: "merge",
      label: "Merge Comedians",
    },
    {
      key: "tags",
      label: "Add Tags",
    }
  ];

  const handleClick = (key: string) => {
    if (key == 'social') {
      socialDataModal.onOpen();
    } else if (key == 'merge') {
      mergeComediansModal.onOpen();
    } else if (key == 'tags') {
      comedianTagModal.onOpen();
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