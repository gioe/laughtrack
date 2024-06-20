'use client'
import Link from "next/link"
import { useState } from "react"
import { Bars3Icon, HomeIcon, XMarkIcon, BuildingStorefrontIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import { Dialog, Disclosure, Popover } from "@headlessui/react"
import { cn } from "@/lib/utils";

const products = [
  {
    name: "Comics",
    href: "#",
    icon: BuildingStorefrontIcon
  },
  {
    name: "Clubs",
    href: "5",
    icon: BuildingStorefrontIcon
  }
]
function Header() {
  const [mobleMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="bg-[#1B262C]">
      <nav
        className="mx-auto flex max-w-7xl items-center justify-between p-6 lg:px-8"
        aria-label="Global">
        <div className="flex lg:flex-1">
          <Link href="/" className="-m-1.5 p-1.5">
            <span className="sr-only">Laugh Track</span>
            <img
              className="h-12 w-auto"
              src="https://paramountshop.com/cdn/shop/files/CC-Mobile-min.png?v=1673463272"
              alt=""
            />
          </Link>
        </div>

        <div className="flex lg:hidden">
          <button type="button"
            className="-m-2.5 inline-flex items-center justify-cetner rounded-md p-2.5 text-white"
            onClick={() => setMobileMenuOpen(true)}>
            <span className="sr-only">Open main menu</span>
            <Bars3Icon className='h-6 w-6' aria-hidden="true" />
          </button>
        </div>

        <Popover.Group className="hidden lg:flex lg:gap-x-12">
          {products.map((item) => {
            return <a href={item.href} className="text-sm font-semibold leading-6 text-white">
              {item.name}
            </a>
          })}
        </Popover.Group>

        <div className="hidden lg:flex lg:flex-1 lg:justify-end">
          <a href="#" className="text-sm font-semibold leading-6 text-white">
            Log in <span aria-hidden="true">&rarr;</span>
          </a>
        </div>

        <Dialog
          as="div"
          className="lg:hidden"
          open={mobleMenuOpen}
          onClose={setMobileMenuOpen}
        >
          <div className="fixed inset-0 z-10" />

          <Dialog.Panel className="fixed inset-y-0 right-0 z-10 w-full
          overflow-y-auto bg-[#1B262C] px-6 py-6 sm:max-w-sm sm:ring-1 sm:ring-gray-900/10">
            <div className="flex items-center jusitfy-between">
              <a href="#" className="-m-1.5 p1.5">
                <span className="sr-only"> Laugh Track </span>
                <img className="h-8 w-auto"
                  src=""
                  alt=""
                />
              </a>
              <button
                type="button"
                className="-m-2.5 rounded-md p-2.5 text-white"
                onClick={() => setMobileMenuOpen(false)}
              >

                <span className="sr-only">Close menu</span>
                <XMarkIcon className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>

            <div className="mt-6 flow-root">
              <div className="-my-6 divide-y divide-gray-500/10">
                <div className="space-y-2 py-6">
                  <Disclosure as="div" className="-mx-3">
                    {
                      ({ open }) => (
                        <>
                          <Disclosure.Button className="flex w-full items-center justify-between rounded-lg py-2 pl-3
                      pr-3.5 text-base font-semibold leading-7 text-white hover:bg-[#3282B8]">
                            Search
                            <ChevronDownIcon
                              className={cn(open ? "rotate-180" : "", "h-5 w-5 flex-none")}
                              aria-hidden="true"
                            />
                          </Disclosure.Button>
                          <Disclosure.Panel className="mt-2 space-y-2">
                            {products.map((item) => {
                              return <Disclosure.Button
                                key={item.name}
                                as="a"
                                href={item.href}
                                className="block rounded-lg py-2 pl-6 pr-3 text-sm font-semibold leading-7 text-white
            hover:bg-[#3282B8]"
                              >
                                {item.name}
                              </Disclosure.Button>
                            })}
                          </Disclosure.Panel>
                        </>
                      )
                    }
                  </Disclosure>
                </div>
                <div className="py-6">
                  <a href="#"
                  className="-mx-3 block rounded-lg px-3 py-2.5 text-base font-semibold leading-7 text-white hover:bg-[#3282B8]"
                  >
                    Log In
                  </a>

                </div>
              </div>
            </div>
          </Dialog.Panel>
        </Dialog>
      </nav>

    </header>
  )
}

export default Header