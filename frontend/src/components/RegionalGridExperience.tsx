"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import RegionalGridMap from "@/components/RegionalGridMap";
import RegionalHistoryTimeline from "@/components/RegionalHistoryTimeline";

import {
  getRegionalGridTimeline,
} from "@/lib/api";

import type {
  RegionalGridSignal,
  RegionalGridTimelinePoint,
} from "@/lib/api";


interface RegionalGridExperienceProps {
  regions: RegionalGridSignal[];
}


function formatPeriod(
  value:
    | string
    | undefined,
): string {
  if (!value) {
    return "LIVE";
  }

  const date =
    new Date(
      value.replace(
        " ",
        "T",
      ),
    );

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return date.toLocaleString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    },
  );
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

  const [
    timeline,
    setTimeline,
  ] = useState<
    RegionalGridTimelinePoint[]
  >([]);

  const [
    frameIndex,
    setFrameIndex,
  ] = useState(
    0,
  );

  const [
    liveMode,
    setLiveMode,
  ] = useState(
    true,
  );

  const [
    playing,
    setPlaying,
  ] = useState(
    false,
  );

  const [
    speedMs,
    setSpeedMs,
  ] = useState(
    650,
  );

  const [
    loading,
    setLoading,
  ] = useState(
    true,
  );

  useEffect(
    () => {
      let cancelled =
        false;

      async function loadTimeline() {
        try {
          const data =
            await getRegionalGridTimeline(
              168,
            );

          if (cancelled) {
            return;
          }

          setTimeline(
            data,
          );

          const uniquePeriods =
            Array.from(
              new Set(
                data.map(
                  (point) =>
                    point.period,
                ),
              ),
            ).sort();

          setFrameIndex(
            Math.max(
              0,
              uniquePeriods.length
              - 1,
            ),
          );
        } catch {
          if (!cancelled) {
            setTimeline([]);
          }
        } finally {
          if (!cancelled) {
            setLoading(
              false,
            );
          }
        }
      }

      void loadTimeline();

      return () => {
        cancelled = true;
      };
    },
    [],
  );

  const periods =
    useMemo(
      () =>
        Array.from(
          new Set(
            timeline.map(
              (point) =>
                point.period,
            ),
          ),
        ).sort(),
      [
        timeline,
      ],
    );

  useEffect(
    () => {
      if (
        !playing
        || liveMode
        || periods.length === 0
      ) {
        return;
      }

      const timer =
        window.setInterval(
          () => {
            setFrameIndex(
              (current) => {
                if (
                  current
                  >= periods.length - 1
                ) {
                  setPlaying(
                    false,
                  );

                  return current;
                }

                return (
                  current + 1
                );
              },
            );
          },
          speedMs,
        );

      return () => {
        window.clearInterval(
          timer,
        );
      };
    },
    [
      liveMode,
      periods.length,
      playing,
      speedMs,
    ],
  );

  const currentPeriod =
    periods[
      frameIndex
    ];

  const historicalFrame =
    useMemo(
      () =>
        timeline.filter(
          (point) =>
            point.period
            === currentPeriod,
        ),
      [
        currentPeriod,
        timeline,
      ],
    );

  const displayRegions:
    RegionalGridSignal[] =
      liveMode
        ? regions
        : historicalFrame;

  const selectedRegion =
    displayRegions.find(
      (region) =>
        region.region
        === selectedCode,
    )
    ?? displayRegions[0]
    ?? regions[0]
    ?? null;

  function play(): void {
    if (
      periods.length === 0
    ) {
      return;
    }

    if (liveMode) {
      setLiveMode(
        false,
      );

      setFrameIndex(
        0,
      );

      setPlaying(
        true,
      );

      return;
    }

    if (
      frameIndex
      >= periods.length - 1
    ) {
      setFrameIndex(
        0,
      );
    }

    setPlaying(
      true,
    );
  }

  function goLive(): void {
    setPlaying(
      false,
    );

    setLiveMode(
      true,
    );

    setFrameIndex(
      Math.max(
        0,
        periods.length - 1,
      ),
    );
  }

  function changeFrame(
    value: number,
  ): void {
    setPlaying(
      false,
    );

    setLiveMode(
      false,
    );

    setFrameIndex(
      value,
    );
  }

  function toggleSpeed(): void {
    setSpeedMs(
      (current) =>
        current === 650
          ? 300
          : 650,
    );
  }

  return (
    <>
      <section className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#050b09]/90">
        <div className="flex flex-col gap-5 px-5 py-4 lg:px-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    liveMode
                      ? "animate-pulse bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.75)]"
                      : "bg-sky-300 shadow-[0_0_12px_rgba(125,211,252,0.65)]"
                  }`}
                />

                <p className="text-[8px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
                  Grid Time Machine
                </p>
              </div>

              <p className="mt-2 text-lg font-medium tracking-[-0.035em] text-white">
                {liveMode
                  ? "Live intelligence snapshot"
                  : formatPeriod(
                      currentPeriod,
                    )}
              </p>

              <p className="mt-1 text-[8px] uppercase tracking-[0.12em] text-white/20">
                {liveMode
                  ? "Latest regional model state"
                  : `${historicalFrame.length} regional signals in frame`}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={
                  playing
                    ? () =>
                        setPlaying(
                          false,
                        )
                    : play
                }
                disabled={
                  loading
                  || periods.length
                    === 0
                }
                className="rounded-lg border border-emerald-300/15 bg-emerald-300/[0.04] px-4 py-2 text-[8px] font-semibold uppercase tracking-[0.14em] text-emerald-200 transition-colors hover:bg-emerald-300/[0.08] disabled:opacity-30"
              >
                {playing
                  ? "Pause"
                  : "Play"}
              </button>

              <button
                type="button"
                onClick={
                  toggleSpeed
                }
                className="rounded-lg border border-white/[0.06] bg-black/25 px-3 py-2 text-[8px] uppercase tracking-[0.14em] text-white/40 hover:text-white/70"
              >
                {speedMs === 650
                  ? "1×"
                  : "2×"}
              </button>

              <button
                type="button"
                onClick={
                  goLive
                }
                className={`rounded-lg border px-4 py-2 text-[8px] font-semibold uppercase tracking-[0.14em] transition-colors ${
                  liveMode
                    ? "border-emerald-300/25 bg-emerald-300/[0.08] text-emerald-200"
                    : "border-white/[0.06] bg-black/25 text-white/35 hover:text-white/70"
                }`}
              >
                Live
              </button>
            </div>
          </div>

          <div>
            <input
              aria-label="Regional historical time"
              type="range"
              min={0}
              max={
                Math.max(
                  0,
                  periods.length - 1,
                )
              }
              value={
                liveMode
                  ? Math.max(
                      0,
                      periods.length - 1,
                    )
                  : frameIndex
              }
              disabled={
                loading
                || periods.length
                  === 0
              }
              onChange={(
                event,
              ) =>
                changeFrame(
                  Number(
                    event.target.value,
                  ),
                )
              }
              className="h-1.5 w-full cursor-pointer accent-emerald-300 disabled:opacity-30"
            />

            <div className="mt-2 flex items-center justify-between text-[7px] uppercase tracking-[0.12em] text-white/20">
              <span>
                {formatPeriod(
                  periods[0],
                )}
              </span>

              <span>
                {loading
                  ? "Loading history"
                  : `${periods.length} time frames`}
              </span>

              <span>
                Latest
              </span>
            </div>
          </div>
        </div>
      </section>

      <RegionalGridMap
        regions={
          displayRegions
        }
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
