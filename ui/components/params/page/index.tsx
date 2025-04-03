"use client";

import TablePagination from "@mui/material/TablePagination";
import { usePageParams } from "./hooks/usePageParams";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const { currentPage, pageSize, updatePage, updatePageSize } =
        usePageParams(itemCount);

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        updatePage(newPageIndex);
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const selectedSize = parseInt(event.target.value);
        updatePageSize(selectedSize);
    };

    return (
        <TablePagination
            sx={{
                ".MuiTablePagination-displayedRows": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-input": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-selectLabel": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-selectIcon": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-actions": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiButtonBase-root": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
            }}
            component="div"
            count={itemCount}
            page={currentPage}
            rowsPerPage={pageSize}
            onPageChange={handleChangeOffset}
            onRowsPerPageChange={handleChangeRows}
        />
    );
}
