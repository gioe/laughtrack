"use client";

import { Dialog, DialogBackdrop, DialogPanel } from "@headlessui/react";
import { FilterOptionsComponent } from "../filters/FilterOptionsComponent";
import { XMarkIcon } from "@heroicons/react/24/outline";

interface SideDrawerComponentProps {
    isOpen: boolean;
    handleOpen: (open: boolean) => void;
}

export function SideDrawerComponent({
    isOpen,
    handleOpen,
}: SideDrawerComponentProps) {
    return (
        <Dialog open={isOpen} onClose={handleOpen} className="relative z-40">
            <DialogBackdrop
                transition
                className="fixed inset-0 bg-white bg-opacity-25 transition-opacity duration-300 ease-linear data-[closed]:opacity-0"
            />

            <div className="fixed inset-0 z-40 flex">
                <DialogPanel
                    transition
                    className="relative ml-auto flex h-full w-full max-w-xs
                             transform flex-col overflow-y-auto bg-shark py-4 pb-12
                              shadow-xl transition duration-300 ease-in-out
                              data-[closed]:translate-x-full"
                >
                    <div className="flex items-center justify-between px-4">
                        <h2 className="text-lg font-medium text-white">
                            Filters
                        </h2>
                        <button
                            type="button"
                            onClick={() => handleOpen(false)}
                            className="-mr-2 flex h-10 w-10 items-center
                                     justify-center rounded-md
                                     bg-shark
                                     p-2
                                      text-white"
                        >
                            <span className="sr-only">Close menu</span>
                            <XMarkIcon aria-hidden="true" className="h-6 w-6" />
                        </button>
                    </div>
                    <FilterOptionsComponent sections={[]} />
                </DialogPanel>
            </div>
        </Dialog>
    );
}
