"use client";
import { FC } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  Pagination,
  PaginationContent,
  PaginationItem,
} from "@/components/ui/pagination";

import { Button } from "@/components/ui/button";
import { handleUrlParams } from "@/lib/utils";

interface PaginationProps {
  pageCount: number;
}

interface PaginationArrowProps {
  direction: "left" | "right";
  handleClick: (direction: string) => void;
  isDisabled: boolean;
}

const PaginationArrow: FC<PaginationArrowProps> = ({
  direction,
  handleClick,
  isDisabled,
}) => {

  const isLeft = direction === "left";
  const disabledClassName = isDisabled ? "opacity-50 cursor-not-allowed" : "";

  return (
    <Button
      onClick={() => handleClick(direction)}
      className={`bg-clear text-gray-500 hover:bg-gray-200 ${disabledClassName}`}
      aria-disabled={isDisabled}
      disabled={isDisabled}
    >
      {isLeft ? "«" : "»"}
    </Button>
  );
};

export function PaginationComponent({ pageCount }: Readonly<PaginationProps>) {
  const searchParams = useSearchParams();
  const pathname = usePathname()
  const { replace } = useRouter()

  const currentPage = Number(searchParams.get("page")) || 1;

  const handleArrowSelection = (direction: string) => {
    const adjustedParams =  handleUrlParams(searchParams, 'page', direction == 'left' ? currentPage - 1 : currentPage + 1)
    replace(`${pathname}?${adjustedParams.toString()}`)
  }

  return (
    <Pagination className="m-5">
      <PaginationContent>
        <PaginationItem>
          <PaginationArrow
            direction="left"
            handleClick={handleArrowSelection}
            isDisabled={currentPage <= 1}
          />
        </PaginationItem>
        <PaginationItem>
          <span className="p-2 font-semibold text-gray-500">
            Page {currentPage}
          </span>
        </PaginationItem>
        <PaginationItem>
          <PaginationArrow
            direction="right"
            handleClick={handleArrowSelection}
            isDisabled={currentPage >= pageCount}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}