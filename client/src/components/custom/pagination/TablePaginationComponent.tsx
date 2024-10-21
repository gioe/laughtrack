"use client";
import { FC, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import TablePagination from '@mui/material/TablePagination';

import { Button } from "@/components/ui/button";
import { handleUrlParams } from "@/lib/utils";

interface TablePaginationComponentProps {
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

export function TablePaginationComponent({ pageCount }: Readonly<TablePaginationComponentProps>) {
  const searchParams = useSearchParams();
  const pathname = usePathname()
  const { replace } = useRouter()

  const currentPage = Number(searchParams.get("page")) || 1;

  const handleArrowSelection = (direction: string) => {
    const adjustedParams =  handleUrlParams(searchParams, 'page', direction == 'left' ? currentPage - 1 : currentPage + 1)
    replace(`${pathname}?${adjustedParams.toString()}`)
  }

  const [page, setPage] = useState(2);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const handleChangePage = (
    event: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number,
  ) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <TablePagination
      component="div"
      count={100}
      page={page}
      onPageChange={handleChangePage}
      rowsPerPage={rowsPerPage}
      onRowsPerPageChange={handleChangeRowsPerPage}
    />
  );
}