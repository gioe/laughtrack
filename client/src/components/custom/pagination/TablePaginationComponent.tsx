"use client";
import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import TablePagination from '@mui/material/TablePagination'
import { handleUrlParams } from "@/lib/utils";

interface TablePaginationComponentProps {
  itemCount: number;
}

export function TablePaginationComponent({ itemCount }: Readonly<TablePaginationComponentProps>) {
  const searchParams = useSearchParams();
  const pathname = usePathname()
  const { replace } = useRouter()

  const currentPage = Number(searchParams.get("page")) || 0;

  const [page, setPage] = useState(currentPage);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const handleChangePage = (
    event: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number,
  ) => {
    const adjustedParams = handleUrlParams(searchParams, 'page', newPage)
    replace(`${pathname}?${adjustedParams.toString()}`)
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const rows = parseInt(event.target.value, 10);
    const adjustedParams = handleUrlParams(searchParams, 'rows', rows)
    replace(`${pathname}?${adjustedParams.toString()}`)
    setRowsPerPage(rows);
    setPage(1);
  };

  return (
    <TablePagination
      sx={{
        ".MuiTablePagination-displayedRows": {
          color: "#C0C0C0",
        },
        ".MuiTablePagination-input": {
          color: "#C0C0C0",
        },
        ".MuiTablePagination-selectLabel": {
          color: "#C0C0C0",
        },
        ".MuiTablePagination-selectIcon": {
          color: "#C0C0C0",
        },
        ".MuiTablePagination-actions": {
          color: "#C0C0C0",
        },
        ".MuiButtonBase-root": {
          color: "#C0C0C0",
        },
      }}
      component="div"
      count={itemCount}
      page={page}
      onPageChange={handleChangePage}
      rowsPerPage={rowsPerPage}
      onRowsPerPageChange={handleChangeRowsPerPage}
    />
  );
}