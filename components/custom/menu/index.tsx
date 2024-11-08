"use client";

import { ModalState } from "../../../objects/interfaces/modalState.interface";
import {
    Dropdown,
    DropdownTrigger,
    DropdownMenu,
    DropdownItem,
    Button,
} from "@nextui-org/react";
import { StoreApi, UseBoundStore } from "zustand";

interface EditClubDowndownProps {
    providedItems: MenuItem[];
}

export interface MenuItem {
    key: string;
    label: string;
    hook: UseBoundStore<StoreApi<ModalState>>;
}

export function Menu({ providedItems }: EditClubDowndownProps) {
    const hookMap = providedItems.map((item) => {
        return {
            key: item.key,
            hook: item.hook(),
        };
    });

    function handleClick(key: string) {
        const hookRecord = hookMap.find((record) => record.key == key);
        hookRecord?.hook.onOpen();
    }

    return (
        <Dropdown>
            <DropdownTrigger>
                <Button variant="bordered" className="bg-white">
                    Open Menu
                </Button>
            </DropdownTrigger>
            <DropdownMenu aria-label="Dynamic Actions" items={providedItems}>
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
}
