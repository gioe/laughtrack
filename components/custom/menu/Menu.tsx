"use client";

import { ModalState } from "../../../interfaces/modalState.interface";
import {
    Dropdown,
    DropdownTrigger,
    DropdownMenu,
    DropdownItem,
    Button,
} from "@nextui-org/react";
import { StoreApi, UseBoundStore } from "zustand";

interface EditClubDowndownProps {
    items: DropdownMenuItem[];
}

export interface DropdownMenuItem {
    key: string;
    label: string;
    store: UseBoundStore<StoreApi<ModalState>>;
}

export const Menu: React.FC<EditClubDowndownProps> = ({ items }) => {
    const handleClick = (key: string) => {
        const item = items.find((item: DropdownMenuItem) => item.key === key);
        item?.store().onOpen();
    };

    return (
        <Dropdown>
            <DropdownTrigger>
                <Button variant="bordered" className="bg-white">
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
                            handleClick(item.key);
                        }}
                    >
                        {item.label}
                    </DropdownItem>
                )}
            </DropdownMenu>
        </Dropdown>
    );
};
