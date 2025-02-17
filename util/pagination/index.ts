import { PaginationData } from "../../objects/interface";

export const buildPaginationData = (data:PaginationData): PaginationData => {
    if (data.index < 1 || data.pageSize <= 0 || data.itemCount < 0) {
        throw new Error('Invalid pagination parameters: All values must be positive');
      }

      const totalPages = Math.ceil(data.itemCount / data.pageSize);
      if (data.itemCount === 0) {
        return {
          ...data,
          index: 0,
        };
      }
      const adjustedPage = Math.min(data.index, totalPages);

      return {
        ...data,
        index: adjustedPage - 1,
      };
}
