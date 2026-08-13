"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  geoAlbersUsa,
  geoPath,
} from "d3-geo";

import {
  feature,
  mesh,
} from "topojson-client";

import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
} from "geojson";

import type {
  GeometryCollection,
  Topology,
} from "topojson-specification";

import type {
  GridRiskSeverity,
  RegionalGridSignal,
} from "@/lib/api";


interface RegionalGridMapProps {
  regions: RegionalGridSignal[];

  selectedCode?: string;

  onSelect?: (
    region: string,
  ) => void;
}


interface RegionCoordinate {
  longitude: number;
  latitude: number;
}


/*
 * Analytical anchor points only.
 * These position regional intelligence signals on the
 * real U.S. geography. They are not EIA boundary polygons.
 */
const REGION_COORDINATES: Record<
  string,
  RegionCoordinate
> = {
  NW: {
    longitude: -120.5,
    latitude: 46.0,
  },

  CAL: {
    longitude: -119.5,
    latitude: 36.8,
  },

  SW: {
    longitude: -111.5,
    latitude: 34.7,
  },

  TEX: {
    longitude: -99.3,
    latitude: 31.2,
  },

  CENT: {
    longitude: -101.0,
    latitude: 40.0,
  },

  MIDW: {
    longitude: -89.5,
    latitude: 42.0,
  },

  TEN: {
    longitude: -86.0,
    latitude: 35.8,
  },

  SE: {
    longitude: -84.5,
    latitude: 32.2,
  },

  FLA: {
    longitude: -81.7,
    latitude: 27.8,
  },

  CAR: {
    longitude: -79.5,
    latitude: 34.8,
  },

  MIDA: {
    longitude: -77.4,
    latitude: 39.4,
  },

  NY: {
    longitude: -75.2,
    latitude: 43.0,
  },

  NE: {
    longitude: -71.4,
    latitude: 43.5,
  },
};


const VIEWBOX_WIDTH =
  975;

const VIEWBOX_HEIGHT =
  610;


function formatNumber(
  value:
    | number
    | null
    | undefined,
  digits = 0,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits:
        digits,
    },
  ).format(value);
}


function formatSignedPercent(
  value:
    | number
    | null
    | undefined,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const prefix =
    value > 0
      ? "+"
      : "";

  return `${prefix}${formatNumber(
    value,
    1,
  )}%`;
}


function formatPercent(
  value:
    | number
    | null
    | undefined,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return `${formatNumber(
    Math.abs(value),
    1,
  )}%`;
}


function severityPalette(
  severity: GridRiskSeverity,
) {
  switch (severity) {
    case "CRITICAL":
      return {
        color: "#fb7185",
        soft: "rgba(251,113,133,0.14)",
        text: "text-rose-300",
        border: "border-rose-400/20",
      };

    case "HIGH":
      return {
        color: "#fdba74",
        soft: "rgba(253,186,116,0.13)",
        text: "text-orange-200",
        border: "border-orange-300/20",
      };

    case "ELEVATED":
      return {
        color: "#fcd34d",
        soft: "rgba(252,211,77,0.12)",
        text: "text-amber-200",
        border: "border-amber-300/20",
      };

    case "NORMAL":
    default:
      return {
        color: "#6ee7b7",
        soft: "rgba(110,231,183,0.11)",
        text: "text-emerald-200",
        border: "border-emerald-300/15",
      };
  }
}


function buildArc(
  start: [
    number,
    number,
  ],
  end: [
    number,
    number,
  ],
): string {
  const [
    startX,
    startY,
  ] = start;

  const [
    endX,
    endY,
  ] = end;

  const middleX =
    (
      startX
      + endX
    )
    / 2;

  const distance =
    Math.abs(
      endX
      - startX,
    );

  const arcHeight =
    Math.min(
      105,
      34
      + distance * 0.12,
    );

  const middleY =
    Math.min(
      startY,
      endY,
    )
    - arcHeight;

  return [
    `M ${startX} ${startY}`,
    `Q ${middleX} ${middleY}`,
    `${endX} ${endY}`,
  ].join(" ");
}


function Metric({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-xl border border-white/[0.055] bg-white/[0.018] p-3">
      <p className="text-[7px] uppercase tracking-[0.14em] text-white/20">
        {label}
      </p>

      <p className="mt-2 text-lg font-medium tracking-[-0.035em] text-white/80">
        {value}
      </p>

      <p className="mt-1 text-[7px] uppercase tracking-[0.11em] text-white/20">
        {helper}
      </p>
    </div>
  );
}


function SignalBar({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  const percentage =
    Math.min(
      100,
      Math.max(
        0,
        score / 4 * 100,
      ),
    );

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[8px] uppercase tracking-[0.12em] text-white/25">
          {label}
        </span>

        <span className="font-mono text-[9px] text-emerald-200/70">
          {formatNumber(
            score,
            2,
          )}
          σ
        </span>
      </div>

      <div className="relative h-[5px] overflow-hidden rounded-full bg-white/[0.045]">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-400/30 via-emerald-300/75 to-white/70 shadow-[0_0_14px_rgba(110,231,183,0.45)]"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  );
}


function ScoreRing({
  score,
  severity,
}: {
  score: number;
  severity: GridRiskSeverity;
}) {
  const palette =
    severityPalette(
      severity,
    );

  const safeScore =
    Math.min(
      100,
      Math.max(
        0,
        score,
      ),
    );

  return (
    <div className="relative flex h-[116px] w-[116px] shrink-0 items-center justify-center">
      <div
        className="absolute inset-0 rounded-full opacity-25 blur-xl"
        style={{
          background:
            palette.color,
        }}
      />

      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(
            ${palette.color}
            ${safeScore * 3.6}deg,
            rgba(255,255,255,0.045)
            ${safeScore * 3.6}deg
          )`,
        }}
      />

      <div className="absolute inset-[6px] rounded-full bg-[#06100d]" />

      <div className="absolute inset-[11px] rounded-full border border-white/[0.05]" />

      <div className="relative text-center">
        <p className="text-3xl font-medium tracking-[-0.06em] text-white">
          {formatNumber(
            score,
            1,
          )}
        </p>

        <p className="mt-1 text-[7px] uppercase tracking-[0.15em] text-white/25">
          pressure
        </p>
      </div>
    </div>
  );
}


export default function RegionalGridMap({
  regions,
  selectedCode:
    controlledSelectedCode,
  onSelect,
}: RegionalGridMapProps) {
  const [
    topology,
    setTopology,
  ] = useState<
    Topology | null
  >(null);

  const [
    internalSelectedCode,
    setInternalSelectedCode,
  ] = useState(
    regions[0]?.region ??
      "",
  );

  const selectedCode =
    controlledSelectedCode
    ?? internalSelectedCode;

  function selectRegion(
    regionCode: string,
  ): void {
    setInternalSelectedCode(
      regionCode,
    );

    onSelect?.(
      regionCode,
    );
  }

  useEffect(
    () => {
      let cancelled =
        false;

      async function loadMap() {
        const response =
          await fetch(
            "/us-states-albers-10m.json",
          );

        if (!response.ok) {
          return;
        }

        const data =
          await response.json() as Topology;

        if (!cancelled) {
          setTopology(
            data,
          );
        }
      }

      void loadMap();

      return () => {
        cancelled = true;
      };
    },
    [],
  );

  const projection =
    useMemo(
      () =>
        geoAlbersUsa()
          .scale(
            1300,
          )
          .translate([
            487.5,
            305,
          ]),
      [],
    );

  const pathGenerator =
    useMemo(
      () => geoPath(),
      [],
    );

  const mapGeometry =
    useMemo(
      () => {
        if (!topology) {
          return null;
        }

        const stateObject =
          topology.objects
            .states as GeometryCollection;

        const nationObject =
          topology.objects
            .nation as GeometryCollection;

        const states =
          feature(
            topology,
            stateObject,
          ) as FeatureCollection<
            Geometry,
            GeoJsonProperties
          >;

        const nation =
          feature(
            topology,
            nationObject,
          ) as Feature<
            Geometry,
            GeoJsonProperties
          >;

        const borders =
          mesh(
            topology,
            stateObject,
            (
              first,
              second,
            ) =>
              first !== second,
          );

        return {
          states,
          nation,
          borders,
        };
      },
      [
        topology,
      ],
    );

  const projectedRegions =
    useMemo(
      () =>
        regions
          .map(
            (region) => {
              const coordinate =
                REGION_COORDINATES[
                  region.region
                ];

              if (!coordinate) {
                return null;
              }

              const point =
                projection([
                  coordinate.longitude,
                  coordinate.latitude,
                ]);

              if (!point) {
                return null;
              }

              return {
                region,
                point,
              };
            },
          )
          .filter(
            (
              item,
            ): item is {
              region:
                RegionalGridSignal;
              point: [
                number,
                number,
              ];
            } =>
              item !== null,
          ),
      [
        projection,
        regions,
      ],
    );

  if (
    regions.length === 0
  ) {
    return (
      <section className="mt-5 rounded-2xl border border-white/[0.07] bg-white/[0.015] p-6">
        <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
          U.S. Grid Intelligence Map
        </p>

        <p className="mt-3 text-sm text-white/35">
          Regional intelligence
          is currently unavailable.
        </p>
      </section>
    );
  }

  const selectedRegion =
    regions.find(
      (region) =>
        region.region ===
        selectedCode,
    )
    ?? projectedRegions[0]
      ?.region
    ?? regions[0];

  const selectedProjected =
    projectedRegions.find(
      (item) =>
        item.region.region ===
        selectedRegion.region,
    );

  const palette =
    severityPalette(
      selectedRegion.severity,
    );

  const strongestConnections =
    projectedRegions
      .filter(
        (item) =>
          item.region.region !==
          selectedRegion.region,
      )
      .sort(
        (
          left,
          right,
        ) =>
          right.region
            .pressure_score
          - left.region
            .pressure_score,
      )
      .slice(
        0,
        6,
      );

  return (
    <section className="mt-5 overflow-hidden rounded-2xl border border-white/[0.075] bg-[#050b09]/90 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
      <div className="flex flex-col justify-between gap-5 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-30" />

              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.8)]" />
            </span>

            <p className="text-[9px] font-semibold uppercase tracking-[0.24em] text-emerald-200">
              U.S. Grid Intelligence
            </p>
          </div>

          <h2 className="mt-2 text-2xl font-medium tracking-[-0.04em] text-white">
            National pressure network
          </h2>

          <p className="mt-2 max-w-[700px] text-[10px] leading-5 text-white/30">
            Real U.S. geography with
            live GridPulse regional
            pressure signals,
            historical baselines,
            and anomaly pathways.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="rounded-full border border-emerald-300/10 bg-emerald-300/[0.035] px-3 py-2 text-[7px] uppercase tracking-[0.14em] text-emerald-200">
            Census geometry
          </div>

          <div className="rounded-full border border-white/[0.06] bg-black/25 px-3 py-2 text-[7px] uppercase tracking-[0.14em] text-white/30">
            {
              projectedRegions.length
            } regional signals
          </div>

          <div className="rounded-full border border-white/[0.06] bg-black/25 px-3 py-2 text-[7px] uppercase tracking-[0.14em] text-white/30">
            Historical model
          </div>
        </div>
      </div>

      <div className="grid xl:grid-cols-[1.5fr_0.5fr]">
        <div className="relative min-h-[650px] overflow-hidden border-b border-white/[0.06] bg-[radial-gradient(circle_at_50%_40%,rgba(16,185,129,0.08),transparent_48%),linear-gradient(180deg,rgba(255,255,255,0.008),transparent)] xl:border-b-0 xl:border-r">
          <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] [background-size:42px_42px]" />

          <div className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[760px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-400/[0.025] blur-[70px]" />

          {!mapGeometry && (
            <div className="absolute inset-0 flex items-center justify-center text-[9px] uppercase tracking-[0.18em] text-white/20">
              Loading U.S.
              topology…
            </div>
          )}

          {mapGeometry && (
            <svg
              className="absolute inset-0 h-full w-full"
              viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
              preserveAspectRatio="xMidYMid meet"
              role="img"
              aria-label="Interactive United States regional grid pressure map"
            >
              <defs>
                <linearGradient
                  id="nationFill"
                  x1="0"
                  x2="1"
                  y1="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor="#0f211b"
                    stopOpacity="0.92"
                  />

                  <stop
                    offset="48%"
                    stopColor="#0a1814"
                    stopOpacity="0.94"
                  />

                  <stop
                    offset="100%"
                    stopColor="#07110e"
                    stopOpacity="0.98"
                  />
                </linearGradient>

                <radialGradient
                  id="mapEnergy"
                >
                  <stop
                    offset="0%"
                    stopColor="#6ee7b7"
                    stopOpacity="0.16"
                  />

                  <stop
                    offset="100%"
                    stopColor="#6ee7b7"
                    stopOpacity="0"
                  />
                </radialGradient>

                <filter
                  id="nationGlow"
                  x="-20%"
                  y="-20%"
                  width="140%"
                  height="140%"
                >
                  <feGaussianBlur
                    stdDeviation="7"
                    result="blur"
                  />

                  <feMerge>
                    <feMergeNode
                      in="blur"
                    />

                    <feMergeNode
                      in="SourceGraphic"
                    />
                  </feMerge>
                </filter>
              </defs>

              <path
                d={
                  pathGenerator(
                    mapGeometry.nation,
                  )
                  ?? undefined
                }
                fill="none"
                stroke="#6ee7b7"
                strokeOpacity="0.13"
                strokeWidth="5"
                filter="url(#nationGlow)"
              />

              {mapGeometry.states.features.map(
                (
                  state,
                  index,
                ) => (
                  <path
                    key={
                      state.id
                      ?? index
                    }
                    d={
                      pathGenerator(
                        state,
                      )
                      ?? undefined
                    }
                    fill="url(#nationFill)"
                    stroke="none"
                  />
                ),
              )}

              <path
                d={
                  pathGenerator(
                    mapGeometry.borders,
                  )
                  ?? undefined
                }
                fill="none"
                stroke="rgba(255,255,255,0.13)"
                strokeWidth="0.75"
                vectorEffect="non-scaling-stroke"
              />

              <path
                d={
                  pathGenerator(
                    mapGeometry.nation,
                  )
                  ?? undefined
                }
                fill="none"
                stroke="#83f7cf"
                strokeOpacity="0.3"
                strokeWidth="1.4"
                vectorEffect="non-scaling-stroke"
              />

              {selectedProjected &&
                strongestConnections.map(
                  (
                    target,
                    index,
                  ) => {
                    const path =
                      buildArc(
                        selectedProjected.point,
                        target.point,
                      );

                    return (
                      <g
                        key={
                          target.region.region
                        }
                      >
                        <path
                          d={path}
                          fill="none"
                          stroke={
                            palette.color
                          }
                          strokeOpacity="0.11"
                          strokeWidth="3"
                        />

                        <path
                          d={path}
                          fill="none"
                          stroke={
                            palette.color
                          }
                          strokeOpacity="0.4"
                          strokeWidth="1"
                          strokeDasharray="5 14"
                        >
                          <animate
                            attributeName="stroke-dashoffset"
                            from="0"
                            to="-95"
                            dur={`${2.6 + index * 0.25}s`}
                            repeatCount="indefinite"
                          />
                        </path>
                      </g>
                    );
                  },
                )}

              {projectedRegions.map(
                (
                  item,
                ) => {
                  const {
                    region,
                    point,
                  } = item;

                  const nodePalette =
                    severityPalette(
                      region.severity,
                    );

                  const selected =
                    region.region ===
                    selectedRegion.region;

                  const radius =
                    11
                    + Math.min(
                      8,
                      region.pressure_score
                      * 0.075,
                    );

                  return (
                    <g
                      key={
                        region.region
                      }
                      role="button"
                      tabIndex={0}
                      aria-label={`Inspect ${region.region_name}`}
                      onClick={() =>
                        selectRegion(
                          region.region,
                        )
                      }
                      onKeyDown={(
                        event,
                      ) => {
                        if (
                          event.key
                            === "Enter"
                          || event.key
                            === " "
                        ) {
                          selectRegion(
                            region.region,
                          );
                        }
                      }}
                      className="cursor-pointer outline-none"
                      style={{
                        filter: `drop-shadow(0 0 ${
                          selected
                            ? 15
                            : 8
                        }px ${nodePalette.color})`,
                      }}
                    >
                      {selected && (
                        <>
                          <circle
                            cx={
                              point[0]
                            }
                            cy={
                              point[1]
                            }
                            r={
                              radius
                              + 9
                            }
                            fill="none"
                            stroke={
                              nodePalette.color
                            }
                            strokeWidth="1"
                            opacity="0.5"
                          >
                            <animate
                              attributeName="r"
                              values={`${radius + 8};${radius + 28};${radius + 8}`}
                              dur="2.8s"
                              repeatCount="indefinite"
                            />

                            <animate
                              attributeName="opacity"
                              values="0.5;0;0.5"
                              dur="2.8s"
                              repeatCount="indefinite"
                            />
                          </circle>

                          <circle
                            cx={
                              point[0]
                            }
                            cy={
                              point[1]
                            }
                            r={
                              radius
                              + 4
                            }
                            fill="url(#mapEnergy)"
                          />
                        </>
                      )}

                      <circle
                        cx={
                          point[0]
                        }
                        cy={
                          point[1]
                        }
                        r={
                          radius
                        }
                        fill="#06100d"
                        stroke={
                          nodePalette.color
                        }
                        strokeOpacity={
                          selected
                            ? 1
                            : 0.58
                        }
                        strokeWidth={
                          selected
                            ? 2
                            : 1
                        }
                      />

                      <circle
                        cx={
                          point[0]
                        }
                        cy={
                          point[1]
                        }
                        r={
                          radius - 4
                        }
                        fill={
                          nodePalette.color
                        }
                        opacity="0.12"
                      />

                      <circle
                        cx={
                          point[0]
                        }
                        cy={
                          point[1]
                        }
                        r="3"
                        fill={
                          nodePalette.color
                        }
                      />

                      <text
                        x={
                          point[0]
                        }
                        y={
                          point[1]
                          - radius
                          - 8
                        }
                        textAnchor="middle"
                        fill={
                          selected
                            ? "#ffffff"
                            : "rgba(255,255,255,0.58)"
                        }
                        fontSize={
                          selected
                            ? 11
                            : 9
                        }
                        fontWeight="600"
                        letterSpacing="1.2"
                      >
                        {
                          region.region
                        }
                      </text>

                      <text
                        x={
                          point[0]
                        }
                        y={
                          point[1]
                          + radius
                          + 13
                        }
                        textAnchor="middle"
                        fill={
                          nodePalette.color
                        }
                        opacity={
                          selected
                            ? 0.9
                            : 0.5
                        }
                        fontSize="8"
                      >
                        {formatNumber(
                          region.pressure_score,
                          1,
                        )}
                      </text>
                    </g>
                  );
                },
              )}
            </svg>
          )}

          <div className="pointer-events-none absolute left-5 top-5 rounded-xl border border-white/[0.06] bg-black/40 px-3 py-2 backdrop-blur-md">
            <p className="text-[7px] uppercase tracking-[0.15em] text-white/25">
              Geographic layer
            </p>

            <p className="mt-1 text-[9px] text-emerald-200/70">
              U.S. Albers projection
            </p>
          </div>

          <div className="pointer-events-none absolute bottom-5 left-5 flex flex-wrap gap-4 rounded-xl border border-white/[0.05] bg-black/35 px-3 py-2 backdrop-blur">
            {[
              [
                "Normal",
                "#6ee7b7",
              ],
              [
                "Elevated",
                "#fcd34d",
              ],
              [
                "High",
                "#fdba74",
              ],
              [
                "Critical",
                "#fb7185",
              ],
            ].map(
              ([
                label,
                color,
              ]) => (
                <div
                  key={label}
                  className="flex items-center gap-1.5"
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{
                      background:
                        color,
                      boxShadow:
                        `0 0 8px ${color}`,
                    }}
                  />

                  <span className="text-[7px] uppercase tracking-[0.12em] text-white/25">
                    {label}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>

        <aside className="relative overflow-hidden bg-[linear-gradient(180deg,rgba(110,231,183,0.025),transparent_45%)] p-5 lg:p-6">
          <div
            className="pointer-events-none absolute right-[-80px] top-[-80px] h-[220px] w-[220px] rounded-full opacity-20 blur-[80px]"
            style={{
              background:
                palette.color,
            }}
          />

          <div className="relative">
            <p className="text-[8px] uppercase tracking-[0.18em] text-white/25">
              Selected intelligence
            </p>

            <div className="mt-4 flex items-center justify-between gap-5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{
                      background:
                        palette.color,
                      boxShadow:
                        `0 0 14px ${palette.color}`,
                    }}
                  />

                  <p
                    className={`text-[8px] font-semibold uppercase tracking-[0.14em] ${palette.text}`}
                  >
                    {
                      selectedRegion.severity
                    }
                  </p>
                </div>

                <p className="mt-3 text-3xl font-medium tracking-[-0.055em] text-white">
                  {
                    selectedRegion.region
                  }
                </p>

                <p className="mt-1 max-w-[190px] text-[10px] leading-4 text-white/30">
                  {
                    selectedRegion.region_name
                  }
                </p>
              </div>

              <ScoreRing
                score={
                  selectedRegion.pressure_score
                }
                severity={
                  selectedRegion.severity
                }
              />
            </div>

            <div className="mt-6 grid grid-cols-2 gap-2">
              <Metric
                label="Demand"
                value={
                  formatNumber(
                    selectedRegion.demand_mwh,
                  )
                }
                helper="MWh"
              />

              <Metric
                label="Baseline"
                value={
                  formatNumber(
                    selectedRegion.demand_baseline_mwh,
                  )
                }
                helper="Historical MWh"
              />

              <Metric
                label="vs baseline"
                value={
                  formatSignedPercent(
                    selectedRegion.demand_vs_baseline_pct,
                  )
                }
                helper="Current load"
              />

              <Metric
                label="1h movement"
                value={
                  formatSignedPercent(
                    selectedRegion.demand_change_pct,
                  )
                }
                helper="Demand trend"
              />
            </div>

            <div className="mt-7 space-y-5">
              <SignalBar
                label="Demand pressure"
                score={
                  selectedRegion.demand_deviation_score
                }
              />

              <SignalBar
                label="Forecast deviation"
                score={
                  selectedRegion.forecast_deviation_score
                }
              />

              <SignalBar
                label="Generation imbalance"
                score={
                  selectedRegion.generation_deviation_score
                }
              />
            </div>

            <div
              className={`mt-7 rounded-xl border ${palette.border} bg-black/20 p-4`}
            >
              <div className="flex items-center justify-between border-b border-white/[0.045] pb-3">
                <span className="text-[8px] uppercase tracking-[0.12em] text-white/25">
                  Forecast error
                </span>

                <span className="font-mono text-[10px] text-white/65">
                  {formatPercent(
                    selectedRegion.forecast_error_pct,
                  )}
                </span>
              </div>

              <div className="flex items-center justify-between border-b border-white/[0.045] py-3">
                <span className="text-[8px] uppercase tracking-[0.12em] text-white/25">
                  Generation gap
                </span>

                <span className="font-mono text-[10px] text-white/65">
                  {formatPercent(
                    selectedRegion.generation_gap_pct,
                  )}
                </span>
              </div>

              <div className="flex items-center justify-between pt-3">
                <span className="text-[8px] uppercase tracking-[0.12em] text-white/25">
                  Historical depth
                </span>

                <span className="font-mono text-[10px] text-white/65">
                  {
                    selectedRegion.history_points
                  }
                  h
                </span>
              </div>
            </div>

            <div className="mt-6">
              <p className="mb-3 text-[7px] uppercase tracking-[0.15em] text-white/20">
                Regional signal rail
              </p>

              <div className="flex flex-wrap gap-2">
                {projectedRegions.map(
                  (
                    item,
                  ) => {
                    const itemPalette =
                      severityPalette(
                        item.region.severity,
                      );

                    const active =
                      item.region.region
                      === selectedRegion.region;

                    return (
                      <button
                        key={
                          item.region.region
                        }
                        type="button"
                        onClick={() =>
                          selectRegion(
                            item.region.region,
                          )
                        }
                        className={`rounded-lg border px-2.5 py-2 text-[8px] font-medium tracking-[0.08em] transition-all ${
                          active
                            ? "border-white/20 bg-white/[0.08] text-white"
                            : "border-white/[0.05] bg-black/20 text-white/35 hover:border-white/10 hover:text-white/65"
                        }`}
                      >
                        <span
                          className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full"
                          style={{
                            background:
                              itemPalette.color,
                            boxShadow:
                              active
                                ? `0 0 8px ${itemPalette.color}`
                                : "none",
                          }}
                        />

                        {
                          item.region.region
                        }
                      </button>
                    );
                  },
                )}
              </div>
            </div>
          </div>
        </aside>
      </div>

      <div className="flex flex-col justify-between gap-2 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.12em] text-white/20 md:flex-row md:items-center lg:px-6">
        <span>
          Census-derived U.S.
          geography · state boundaries
          shown for spatial context
        </span>

        <span>
          Regional markers are
          analytical anchors · not
          official EIA boundary polygons
        </span>
      </div>
    </section>
  );
}
