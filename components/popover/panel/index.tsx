import { PopoverPanel } from "@headlessui/react";

interface NavbarPopoverItemModel {
    name: string;
    description: string;
    href: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: any;
}

interface NavbarPopoverItemProps {
    items: NavbarPopoverItemModel[];
}

const NavbarPopoverItem: React.FC<NavbarPopoverItemProps> = ({ items }) => {
    return (
        <>
            <PopoverPanel
                transition
                className="absolute -left-8 top-full z-10 mt-3 w-screen max-w-md overflow-hidden rounded-3xl
                 bg-white shadow-lg ring-1 ring-gray-900/5 transition 
                 data-[closed]:translate-y-1 data-[closed]:opacity-0 data-[enter]:duration-200 
                 data-[leave]:duration-150 data-[enter]:ease-out data-[leave]:ease-in"
            >
                <div className="p-4">
                    {items.map((item) => (
                        <div
                            key={item.name}
                            className="group relative flex items-center gap-x-6 
                            rounded-lg p-4 text-sm leading-6 hover:bg-gray-50"
                        >
                            <div
                                className="flex h-11 w-11 flex-none items-center justify-center 
                            rounded-lg group-hover:bg-gray-50"
                            >
                                <item.icon
                                    aria-hidden="true"
                                    className="h-6 w-6 text-gray-600
                                    group-hover:text-copper"
                                />
                            </div>
                            <div className="flex-auto">
                                <a
                                    href={item.href}
                                    className="block font-semibold text-gray-900"
                                >
                                    {item.name}
                                    <span className="absolute inset-0" />
                                </a>
                                <p className="mt-1 text-gray-600">
                                    {item.description}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </PopoverPanel>
        </>
    );
};

export default NavbarPopoverItem;
