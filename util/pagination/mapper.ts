import { PaginationData } from "../../objects/interface";

export const toPaginatedData = (
    input: any[],
    page?: string,
    rows?: string,
): PaginationData => {
    const currentPage = parseInt(page ?? "0") + 1;
    const rowsInt = parseInt(rows ?? "10");
    const startIndex = (currentPage - 1) * rowsInt;
    const endIndex = currentPage * rowsInt;

    const paginatedData = input.slice(startIndex, endIndex);
    const totalPages = Math.ceil(input.length / rowsInt);

    return {
        data: paginatedData,
        totalPages: isNaN(totalPages) ? 0 : totalPages,
    };
};
