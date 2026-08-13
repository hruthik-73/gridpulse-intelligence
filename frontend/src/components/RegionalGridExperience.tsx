"use client";

import {
  useMemo,
  useState,
} from "react";

import RegionalGridMap from "@/components/RegionalGridMap";
import RegionalHistoryTimeline from "@/components/RegionalHistoryTimeline";

import type {
  RegionalGridSignal,
} from "@/lib/api";


interface RegionalGridExperienceProps {
  regions: RegionalGridSignal[];
}


export default function RegionalGridExperience({
  regions,
}: RegionalGridExperienceProps) {
  const [
    selectedCode,
    setSelectedCode,
  ] = useState(
    regions[0]?.region
      ?? "",
  );

  const selectedRegion =
    useMemo(
      () =>
        regions.find(
          (region) =>
            region.region
            === selectedCode,
        )
        ?? regions[0]
        ?? null,
      [
        regions,
        selectedCode,
      ],
    );

  return (
    <>
      <RegionalGridMap
        regions={regions}
        selectedCode={
          selectedRegion
            ?.region
          ?? ""
        }
        onSelect={
          setSelectedCode
        }
      />

      <RegionalHistoryTimeline
        region={
          selectedRegion
        }
      />
    </>
  );
}
