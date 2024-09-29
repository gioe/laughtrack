'use client';

import React, { useState } from 'react';
import { Map, ViewStateChangeEvent, Marker, Popup } from 'react-map-gl'
import * as turf from '@turf/turf';
import getCenter from 'geolib/es/getCenter'
import { MapCoordinate } from '@/interfaces/mapCoordinate.interface';

const GEOFENCE = turf.circle([-74.0122106, 40.7467898], 5, { units: 'miles' });

interface MapComponentInterface {
  coordinates: MapCoordinate[];
  onSelectCoordinate: (coordinate: MapCoordinate | null) => void;
}

const MapComponent: React.FC<MapComponentInterface> = ({
  coordinates, 
  onSelectCoordinate
}) => {


  const handleSelectedCoordinate = (coordinate: MapCoordinate | null) => {
    setSelectedCoordinate(coordinate) 
    onSelectCoordinate(coordinate)
  }
  
  const [selectedCoordinate, setSelectedCoordinate] = useState<MapCoordinate | null>(null)

  const center = getCenter(coordinates);

  if (!center) throw new Error('points is an empty array')

  const [viewState, setViewState] = useState({
    longitude: center.longitude,
    latitude: center.latitude,
    zoom: 12
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

  return (

    <>
      <Map
        mapStyle={process.env.mapbox_style}
        mapboxAccessToken={process.env.mapbox_key}
        style={{ width: "100%", height: "100%" }}
        {...viewState}
      >
        {coordinates.map((coordinate: MapCoordinate) => {
          return (
            <div key={coordinate.longitude}>
              <Marker
                longitude={coordinate.longitude}
                latitude={coordinate.latitude}
                offset={[-20, -10]}
              >
                <p
                  role='img'
                  onClick={() => {
                    handleSelectedCoordinate(coordinate)
                  }}
                  className='cursor-pointer text-2xl'
                  aria-label='push-pin'>
                  📍
                </p>

              </Marker>
            </div>
          )
        }
        )}

      </Map>
    </>
  )

}

export default MapComponent;