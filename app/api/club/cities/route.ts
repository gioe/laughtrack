import * as clubController from "../../../../controllers/club"
import { NextRequest, NextResponse } from 'next/server';

export async function POST(
  req: NextRequest) {

  const cities: string[] = await clubController.getAllCities()

  return NextResponse.json(cities, {
    status: 200,
  })
  
}