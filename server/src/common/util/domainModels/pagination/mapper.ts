import { PaginationData } from "../../../models/interfaces/pagination.interface.js"


export const toPaginatedData = (input: any[], page: string, rows: string): PaginationData => {
    const currentPage = parseInt(page as string) + 1;
    const rowsInt = parseInt(rows as string);
    const startIndex = (currentPage - 1) * rowsInt;
    const endIndex = currentPage * rowsInt;

    const paginatedData = input.slice(startIndex, endIndex);
    const totalPages = Math.ceil(input.length / rowsInt);

    return {
        data: paginatedData,
        totalPages: isNaN(totalPages) ? 0 : totalPages
    }
}
