'use client';

import React, { useState } from 'react';
import { Map, ViewStateChangeEvent, Marker, Popup } from 'react-map-gl'
import * as turf from '@turf/turf';
import getCenter from 'geolib/es/getCenter'
import { ComedianInterface } from '@/interfaces/comedian.interface';
import { ShowInterface } from '@/interfaces/show.interface';
import { ClubInterface } from '@/interfaces/club.interface';
import { SearchResult } from '@/interfaces/searchResult.interface';

const GEOFENCE = turf.circle([-74.0122106, 40.7467898], 5, { units: 'miles' });

interface MapComponentInterface {
  searchResults: SearchResult[];
}

const MapComponent: React.FC<MapComponentInterface> = ({
  searchResults
}) => {

  const [selectedClub, setSelectedClub] = useState<ClubInterface | null>(null)

  const clubs = searchResults
  .flatMap((comedian: ComedianInterface) => comedian.shows)
  .map((show: ShowInterface) => show.club)

  const clubStrings = clubs.map((club: ClubInterface) => JSON.stringify(club))
  const uniqueClubStrings = [...new Set(clubStrings)]
  const coordinates = uniqueClubStrings.map((club:string) => JSON.parse(club))

  .map((club: ClubInterface) => {
    return {latitude: club.latitude, longitude: club.longitude}
  })

  const center = getCenter([]);
  
  if (!center) throw new Error('points is an empty array')

  const [viewState, setViewState] = useState({
    longitude: center.longitude,
    latitude: center.latitude,
    zoom: 3.5
  });

  const onMove = React.useCallback((e: ViewStateChangeEvent) => {
    const newCenter = [e.viewState.longitude, e.viewState.latitude];

    if (turf.booleanPointInPolygon(newCenter, GEOFENCE)) {
      setViewState({
        ...viewState,
        latitude: e.viewState.latitude,
        longitude: e.viewState.longitude
      });
    }
  }, [])


  return <Map
    mapStyle='mapbox://styles/laughtrack-admin/cm17uo0oo009001qkgfby7q5s'
    mapboxAccessToken={process.env.mapbox_key}
    style={{ width: "100%", height: "100%" }}
    {...viewState}
    onMove={onMove}
  >
    {clubs.map((club: ClubInterface) => {
      return (
        <div key={club.longitude}>
          <Marker
            longitude={club.longitude}
            latitude={club.latitude}
            offset={[-20, -10]}
          >
            <p
              role='img'
              onClick={() => setSelectedClub(club)}
              className='cursor-pointer text-2xl animate-bounce'
              aria-label='push-pin'>
              📍
            </p>

          </Marker>

          {club.longitude === club.longitude ?
            (
              <Popup
                latitude={club.latitude}
                longitude={club.longitude}
                onClose={() => setSelectedClub(null)}
                closeOnClick={true}>
                {club.name}
              </Popup>
            ) :
            (
              false
            )}
        </div>
      )
    }
    )}

  </Map>

}

export default MapComponent;