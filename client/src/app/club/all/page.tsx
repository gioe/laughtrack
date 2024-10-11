import { Suspense } from 'react';
import { getClubs, GetClubsParams, GetClubsResponse } from "@/actions/clubs/getClubs";
import ClubTable from "@/components/custom/tables/ClubTable";
import FilterPageContainer from '@/components/custom/filters/FilterPageContainer';

const sortOptions = [
  { name: 'Most Popular', value: 'popularity' },
  { name: 'A-Z', value: 'alphabetically' },
]

const filters = [
  {
      id: 'color',
      name: 'Color',
      options: [
          { value: 'white', label: 'White', selected: false },
          { value: 'beige', label: 'Beige', selected: false },
          { value: 'blue', label: 'Blue', selected: true },
          { value: 'brown', label: 'Brown', selected: false },
          { value: 'green', label: 'Green', selected: false },
          { value: 'purple', label: 'Purple', selected: false },
      ],
  },
  {
      id: 'category',
      name: 'Category',
      options: [
          { value: 'new-arrivals', label: 'New Arrivals', selected: false },
          { value: 'sale', label: 'Sale', selected: false },
          { value: 'travel', label: 'Travel', selected: true },
          { value: 'organization', label: 'Organization', selected: false },
          { value: 'accessories', label: 'Accessories', selected: false },
      ],
  },
  {
      id: 'size',
      name: 'Size',
      options: [
          { value: '2l', label: '2L', selected: false },
          { value: '6l', label: '6L', selected: false },
          { value: '12l', label: '12L', selected: false },
          { value: '18l', label: '18L', selected: false },
          { value: '20l', label: '20L', selected: false },
          { value: '40l', label: '40L', selected: true },
      ],
  },
]

export default async function AllClubsPage({
  searchParams,
}: {
  searchParams?: GetClubsParams;
}) {

  const response = await getClubs(searchParams) as GetClubsResponse

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer filters={filters} sortOptions={sortOptions} title={"Clubs"} child={
        <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
          <ClubTable response={response}  />
        </Suspense>
      } />
    </main>
  );
}
