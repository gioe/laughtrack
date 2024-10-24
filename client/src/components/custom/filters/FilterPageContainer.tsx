'use client'

import { ReactNode, useState } from 'react'
import {
    Dialog,
    DialogBackdrop,
    DialogPanel,
    Disclosure,
    DisclosureButton,
    DisclosurePanel,
    Menu,
    MenuButton,
    MenuItem,
    MenuItems,
} from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { ChevronDownIcon, FunnelIcon, MinusIcon, PlusIcon } from '@heroicons/react/20/solid'
import { cn, handleUrlParams } from '@/lib/utils'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { TablePaginationComponent } from '../pagination/TablePaginationComponent'
import { SortOptionInterface } from '@/interfaces/sortOption.interface'

export interface FilterOption {
    value: string;
    label: string;
    selected: boolean;
}

export interface Filter {
    id: string,
    name: string,
    options: FilterOption[]
}

interface FilterPageContainerProps {
    title?: string;
    child: ReactNode;
    sortOptions: SortOptionInterface[];
    defaultSort: string;
    filterOptions?: Filter[];
    query?: string;
    itemCount: number;
    searchPlaceholder: string
}

const FilterPageContainer: React.FC<FilterPageContainerProps> = ({
    title,
    itemCount,
    child,
    sortOptions,
    filterOptions,
    defaultSort
}) => {

    const [selectedSort, setSelectedSort] = useState(defaultSort)
    const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)

    const pathname = usePathname();
    const searchParams = useSearchParams();
    const { replace } = useRouter();

    const appendFilterParams = (type: string, filter: string) => {
        const adjustedParams = handleUrlParams(searchParams, type, filter)
        replace(`${pathname}?${adjustedParams.toString()}`)
    };

    const handleSortSelection = (sortValue: string) => {
        setSelectedSort(sortValue)
        const adjustedParams = handleUrlParams(searchParams, 'sort', sortValue)
        replace(`${pathname}?${adjustedParams.toString()}`)
    }

    return (
        <div className="bg-shark">
            <div>
                <Dialog open={mobileFiltersOpen} onClose={setMobileFiltersOpen} className="relative z-40">
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
                                <h2 className="text-lg font-medium text-white">Filters</h2>
                                <button
                                    type="button"
                                    onClick={() => setMobileFiltersOpen(false)}
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

                            <form className="mt-4 border-t border-gray-200">
                                {filterOptions && filterOptions.map((section) => (
                                    <Disclosure key={section.id} as="div" className="border-t border-gray-200 px-4 py-6">
                                        <h3 className="-mx-2 -my-3 flow-root">
                                            <DisclosureButton className="group flex w-full items-center
                                             justify-between bg-shark px-2 py-3
                                              text-white hover:text-gray-500">
                                                <span className="font-medium text-white">{section.name}</span>
                                                <span className="ml-6 flex items-center">
                                                    <PlusIcon aria-hidden="true" className="h-5 w-5 group-data-[open]:hidden" />
                                                    <MinusIcon aria-hidden="true" className="h-5 w-5 [.group:not([data-open])_&]:hidden" />
                                                </span>
                                            </DisclosureButton>
                                        </h3>
                                        <DisclosurePanel className="pt-6">
                                            <div className="space-y-2">
                                                {section.options.map((option, optionIdx) => (
                                                    <div key={option.value} className="flex items-center">
                                                        <input
                                                            onClick={() => appendFilterParams(section.id, option.value)}
                                                            defaultValue={option.value}
                                                            defaultChecked={option.selected}
                                                            id={`filter-mobile-${section.id}-${optionIdx}`}
                                                            name={`${section.id}[]`}
                                                            type="checkbox"
                                                            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                                        />
                                                        <label
                                                            htmlFor={`filter-mobile-${section.id}-${optionIdx}`}
                                                            className="ml-3 min-w-0 flex-1 text-silver-gray"
                                                        >
                                                            {option.label}
                                                        </label>
                                                    </div>
                                                ))}
                                            </div>
                                        </DisclosurePanel>
                                    </Disclosure>
                                ))}
                            </form>
                        </DialogPanel>
                    </div>
                </Dialog>

                <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                    <div className="flex items-baseline justify-between border-b border-gray-200 pb-6 pt-10 bg-blue-gray-900">
                        {title && <h1 className="text-3xl font-bold tracking-tight text-white">{title}</h1>}
                    </div>

                    <section aria-labelledby="filters-heading" className="pb-10 pt-5">
                        <div className="flex flex-row-reverse gap-4 items-center">
                            <div className='flex-item tems-end justify-end'>
                                <button
                                    type="button"
                                    onClick={() => setMobileFiltersOpen(true)}
                                    className="-m-2 ml-4 p-2 text-gray-400 hover:text-gray-500 sm:ml-6"
                                >
                                    <span className="sr-only">Filters</span>
                                    <FunnelIcon aria-hidden="true" className="h-5 w-5" />
                                </button>
                            </div>

                            <Menu as="div" className="flex-item items-end relative inline-block text-left">
                                <div>
                                    <MenuButton className="group inline-flex justify-center text-sm font-medium text-gray-300 hover:text-gray-500">
                                        Sort
                                        <ChevronDownIcon
                                            aria-hidden="true"
                                            className="-mr-1 ml-1 h-5 w-5 flex-shrink-0 text-gray-400 group-hover:text-gray-500"
                                        />
                                    </MenuButton>
                                </div>

                                <MenuItems
                                    transition
                                    className="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-md
                                     bg-white shadow-2xl ring-1 ring-black ring-opacity-5 transition focus:outline-none 
                                     data-[closed]:scale-95 data-[closed]:transform data-[closed]:opacity-0 data-[enter]:duration-100
                                      data-[leave]:duration-75 data-[enter]:ease-out data-[leave]:ease-in"
                                >
                                    <div className="py-1">
                                        {sortOptions.map((option) => (
                                            <MenuItem key={option.name}>
                                                <h1
                                                    onClick={() => handleSortSelection(option.value)}
                                                    className={cn(
                                                        option.value == selectedSort ? 'font-medium text-gray-900 cursor-pointer' : 'text-gray-500',
                                                        'block px-4 py-2 text-sm data-[focus]:bg-gray-100 cursor-pointer',
                                                    )}
                                                >
                                                    {option.name}
                                                </h1>
                                            </MenuItem>
                                        ))}
                                    </div>
                                </MenuItems>
                            </Menu>
                            <div className='flex-item items-end'>
                                {itemCount > 0 && <TablePaginationComponent itemCount={itemCount} />}
                            </div>
                        </div>
                        <div className="grid grid-cols-1 gap-x-8 gap-y-10 lg:grid-cols-5">
                            <div className="lg:col-span-4">{child}</div>
                        </div>
                    </section>

                </main>
            </div>
        </div>
    )
}

export default FilterPageContainer;