'use client';

import useAddClubTagModal from "@/hooks/useAddClubTagModal";
import useClearShowsModal from "@/hooks/useClearShowsModal";
import useRunScrapeModal from "@/hooks/useRunScrapeModal";
import {Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button} from "@nextui-org/react";

export const EditClubDowndown = () => {

  const runScrapeModal = useRunScrapeModal();
  const clearShowsModal = useClearShowsModal();
  const clubTagModal = useAddClubTagModal();

  const items = [
    {
      key: "clear",
      label: "Clear Shows",
    },
    {
      key: "scrape",
      label: "Run Scrape",
    },
    {
      key: "tags",
      label: "Add Tags",
    }
  ];

  const handleClick = (key: string) => {
    if (key == 'clear') {
      clearShowsModal.onOpen();
    } else  if (key == 'scrape') {
      runScrapeModal.onOpen();
    } else  if (key == 'tags') {
      clubTagModal.onOpen();
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