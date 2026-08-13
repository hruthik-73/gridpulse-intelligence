"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getPipelineLineage,
} from "@/lib/api";

import type {
  PipelineLineage,
  PipelineLineageNode,
  PipelineNodeState,
} from "@/lib/api";


function nodeStyle(
  state: PipelineNodeState,
) {
  switch (state) {
    case "HEALTHY":
      return {
        color: "#6ee7b7",
        text:
          "text-emerald-200",
      };

    case "DEGRADED":
      return {
        color: "#fcd34d",
        text:
          "text-amber-200",
      };

    case "UNHEALTHY":
      return {
        color: "#fb7185",
        text:
          "text-rose-300",
      };

    case "UNKNOWN":
    default:
      return {
        color:
          "rgba(255,255,255,0.30)",
        text:
          "text-white/35",
      };
  }
}


function runColor(
  status:
    PipelineLineageNode[
      "latest_run_status"
    ],
): string {
  switch (status) {
    case "SUCCEEDED":
      return "#6ee7b7";

    case "FAILED":
      return "#fb7185";

    case "STARTED":
      return "#7dd3fc";

    default:
      return "rgba(255,255,255,0.22)";
  }
}


function formatDuration(
  value:
    | number
    | null,
): string {
  if (value === null) {
    return "—";
  }

  if (value < 1) {
    return `${Math.max(
      1,
      Math.round(
        value * 1000,
      ),
    )} ms`;
  }

  if (value < 60) {
    return `${value.toFixed(
      1,
    )}s`;
  }

  return `${(
    value / 60
  ).toFixed(1)}m`;
}


function formatTime(
  value:
    | string
    | null,
): string {
  if (!value) {
    return "—";
  }

  const date =
    new Date(
      value,
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
      second: "2-digit",
    },
  );
}


export default function PipelineLineagePanel() {
  const [
    lineage,
    setLineage,
  ] = useState<
    PipelineLineage
    | null
  >(null);

  const [
    selectedNodeId,
    setSelectedNodeId,
  ] = useState<
    string
    | null
  >(null);

  useEffect(
    () => {
      let cancelled =
        false;

      async function loadLineage() {
        try {
          const data =
            await getPipelineLineage();

          if (!cancelled) {
            setLineage(
              data,
            );

            setSelectedNodeId(
              data.nodes[0]
                ?.node_id
              ?? null,
            );
          }
        } catch {
          if (!cancelled) {
            setLineage(
              null,
            );
          }
        }
      }

      void loadLineage();

      return () => {
        cancelled = true;
      };
    },
    [],
  );

  const nodesById =
    useMemo(
      () =>
        new Map(
          lineage?.nodes.map(
            (node) => [
              node.node_id,
              node,
            ],
          )
          ?? [],
        ),
      [
        lineage,
      ],
    );

  const selectedNode =
    selectedNodeId
      ? nodesById.get(
          selectedNodeId,
        )
      : undefined;

  if (!lineage) {
    return (
      <section className="mt-5 rounded-2xl border border-white/[0.07] bg-white/[0.012] p-6">
        <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
          Pipeline Lineage Intelligence
        </p>

        <p className="mt-3 text-sm text-white/30">
          Lineage intelligence is
          currently unavailable.
        </p>
      </section>
    );
  }

  const unhealthy =
    lineage.nodes.filter(
      (node) =>
        node.state
        === "UNHEALTHY",
    ).length;

  const degraded =
    lineage.nodes.filter(
      (node) =>
        node.state
        === "DEGRADED",
    ).length;

  const instrumented =
    lineage.nodes.filter(
      (node) =>
        node.latest_run_status
        !== null,
    ).length;

  return (
    <section
      id="pipeline-lineage"
      className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#050b09]/90"
    >
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.75)]" />

            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
              Pipeline Lineage Intelligence
            </p>
          </div>

          <h2 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            From source to decision
          </h2>

          <p className="mt-1 max-w-[760px] text-[10px] leading-5 text-white/30">
            Runtime health,
            source freshness, and
            verified execution
            telemetry across the
            GridPulse data path.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="rounded-full border border-emerald-300/10 bg-emerald-300/[0.025] px-3 py-2 text-[8px] text-emerald-200/60">
            {instrumented}
            {" "}
            instrumented
          </div>

          <div className="rounded-full border border-amber-300/10 bg-amber-300/[0.025] px-3 py-2 text-[8px] text-amber-200/60">
            {degraded}
            {" "}
            degraded
          </div>

          <div className="rounded-full border border-rose-400/10 bg-rose-400/[0.025] px-3 py-2 text-[8px] text-rose-300/60">
            {unhealthy}
            {" "}
            unhealthy
          </div>
        </div>
      </div>

      <div className="grid xl:grid-cols-[1.55fr_0.45fr]">
        <div className="relative min-h-[560px] overflow-hidden border-b border-white/[0.06] bg-[radial-gradient(circle_at_50%_50%,rgba(16,185,129,0.055),transparent_48%)] xl:border-b-0 xl:border-r">
          <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] [background-size:40px_40px]" />

          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 1000 560"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <defs>
              <linearGradient
                id="pipelineEdge"
                x1="0"
                x2="1"
              >
                <stop
                  offset="0%"
                  stopColor="#6ee7b7"
                  stopOpacity="0.12"
                />

                <stop
                  offset="50%"
                  stopColor="#6ee7b7"
                  stopOpacity="0.55"
                />

                <stop
                  offset="100%"
                  stopColor="#6ee7b7"
                  stopOpacity="0.12"
                />
              </linearGradient>
            </defs>

            {lineage.edges.map(
              (edge) => {
                const source =
                  nodesById.get(
                    edge.source_node,
                  );

                const target =
                  nodesById.get(
                    edge.target_node,
                  );

                if (
                  !source
                  || !target
                ) {
                  return null;
                }

                const x1 =
                  source.position_x
                  * 10;

                const y1 =
                  source.position_y
                  * 5.6;

                const x2 =
                  target.position_x
                  * 10;

                const y2 =
                  target.position_y
                  * 5.6;

                const middle =
                  (
                    x1
                    + x2
                  )
                  / 2;

                const path =
                  `M ${x1} ${y1} `
                  + `C ${middle} ${y1}, `
                  + `${middle} ${y2}, `
                  + `${x2} ${y2}`;

                return (
                  <g
                    key={
                      edge.edge_id
                    }
                  >
                    <path
                      d={path}
                      fill="none"
                      stroke="rgba(110,231,183,0.07)"
                      strokeWidth="5"
                    />

                    <path
                      d={path}
                      fill="none"
                      stroke="url(#pipelineEdge)"
                      strokeWidth="1.4"
                      strokeDasharray="8 14"
                    >
                      <animate
                        attributeName="stroke-dashoffset"
                        from="0"
                        to="-88"
                        dur="3s"
                        repeatCount="indefinite"
                      />
                    </path>
                  </g>
                );
              },
            )}
          </svg>

          {lineage.nodes.map(
            (node) => {
              const style =
                nodeStyle(
                  node.state,
                );

              const selected =
                node.node_id
                === selectedNodeId;

              const executionColor =
                runColor(
                  node.latest_run_status,
                );

              return (
                <button
                  key={
                    node.node_id
                  }
                  type="button"
                  onClick={() =>
                    setSelectedNodeId(
                      node.node_id,
                    )
                  }
                  className="group absolute z-10 -translate-x-1/2 -translate-y-1/2 outline-none"
                  style={{
                    left:
                      `${node.position_x}%`,
                    top:
                      `${node.position_y}%`,
                  }}
                >
                  {selected && (
                    <span
                      className="absolute left-1/2 top-1/2 h-20 w-20 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full opacity-10 blur-xl"
                      style={{
                        background:
                          style.color,
                      }}
                    />
                  )}

                  <span
                    className={`relative flex min-w-[78px] flex-col items-center rounded-xl border bg-[#07110e]/95 px-3 py-3 backdrop-blur transition-all duration-300 ${
                      selected
                        ? "scale-110 border-white/20 shadow-[0_12px_35px_rgba(0,0,0,0.4)]"
                        : "border-white/[0.07] group-hover:scale-105 group-hover:border-white/15"
                    }`}
                  >
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{
                        background:
                          style.color,
                        boxShadow:
                          `0 0 12px ${style.color}`,
                      }}
                    />

                    <span className="mt-2 whitespace-nowrap text-[9px] font-semibold text-white/80">
                      {node.label}
                    </span>

                    <span className="mt-1 whitespace-nowrap text-[6px] uppercase tracking-[0.1em] text-white/20">
                      {node.layer}
                    </span>

                    {node.run_stage && (
                      <span className="mt-2 flex items-center gap-1.5 border-t border-white/[0.045] pt-2">
                        <span
                          className="h-1 w-1 rounded-full"
                          style={{
                            background:
                              executionColor,
                            boxShadow:
                              `0 0 6px ${executionColor}`,
                          }}
                        />

                        <span className="text-[6px] uppercase tracking-[0.08em] text-white/25">
                          {node.latest_run_status
                            ?? "NO RUN"}
                        </span>
                      </span>
                    )}
                  </span>
                </button>
              );
            },
          )}
        </div>

        <aside className="bg-black/15 p-5 lg:p-6">
          {selectedNode ? (
            <NodeInspector
              node={
                selectedNode
              }
            />
          ) : (
            <p className="text-sm text-white/25">
              Select a pipeline node.
            </p>
          )}
        </aside>
      </div>

      <div className="flex flex-wrap gap-5 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.11em] text-white/20 lg:px-6">
        <span>
          Source freshness
        </span>

        <span>
          Runtime health
        </span>

        <span>
          Verified executions
        </span>

        <span>
          Failure history
        </span>

        <span>
          Lineage
        </span>
      </div>
    </section>
  );
}


function NodeInspector({
  node,
}: {
  node: PipelineLineageNode;
}) {
  const style =
    nodeStyle(
      node.state,
    );

  const executionColor =
    runColor(
      node.latest_run_status,
    );

  return (
    <div>
      <p className="text-[8px] uppercase tracking-[0.17em] text-white/25">
        Selected pipeline node
      </p>

      <div className="mt-4 flex items-center gap-3">
        <span
          className="h-2 w-2 rounded-full"
          style={{
            background:
              style.color,
            boxShadow:
              `0 0 14px ${style.color}`,
          }}
        />

        <span
          className={`text-[9px] font-semibold uppercase tracking-[0.14em] ${style.text}`}
        >
          {node.state}
        </span>
      </div>

      <h3 className="mt-4 text-3xl font-medium tracking-[-0.05em] text-white">
        {node.label}
      </h3>

      <p className="mt-1 text-[9px] text-white/30">
        {node.technology}
        {" · "}
        {node.layer}
      </p>

      <div className="mt-6 rounded-xl border border-white/[0.055] bg-black/20 p-4">
        <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
          Current evidence
        </p>

        <p className="mt-2 text-[10px] leading-5 text-white/40">
          {node.detail}
        </p>
      </div>

      {node.run_stage && (
        <div className="mt-3 rounded-xl border border-white/[0.06] bg-black/20 p-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
              Execution telemetry
            </p>

            <div className="flex items-center gap-2">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  background:
                    executionColor,
                  boxShadow:
                    `0 0 8px ${executionColor}`,
                }}
              />

              <span className="text-[8px] font-semibold text-white/50">
                {node.latest_run_status
                  ?? "NO EXECUTION DATA"}
              </span>
            </div>
          </div>

          <div className="mt-4 space-y-3 border-t border-white/[0.045] pt-4">
            <InspectorRow
              label="Stage"
              value={
                node.run_stage
              }
              mono
            />

            <InspectorRow
              label="Last duration"
              value={
                formatDuration(
                  node.latest_run_duration_seconds,
                )
              }
            />

            <InspectorRow
              label="Latest run"
              value={
                formatTime(
                  node.latest_run_started_at,
                )
              }
            />

            <InspectorRow
              label="Last success"
              value={
                formatTime(
                  node.last_success_at,
                )
              }
            />

            <InspectorRow
              label="Recent runs"
              value={
                String(
                  node.recent_runs,
                )
              }
            />

            <InspectorRow
              label="Recent failures"
              value={
                String(
                  node.recent_failures,
                )
              }
              alert={
                node.recent_failures
                > 0
              }
            />
          </div>
        </div>
      )}

      {node.run_stage && (
        <div className="mt-3 rounded-xl border border-sky-300/[0.07] bg-sky-300/[0.018] p-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-[7px] uppercase tracking-[0.13em] text-sky-200/45">
              GridPulse operational SLA
            </p>

            <span
              className={`text-[8px] font-semibold ${
                node.operational_status === "FAILED"
                || node.operational_status === "STALLED"
                  ? "text-rose-300"
                  : node.operational_status === "OVERDUE"
                    ? "text-amber-200"
                    : node.operational_status === "RUNNING"
                      ? "text-sky-200"
                      : node.operational_status === "SUCCEEDED"
                        ? "text-emerald-200"
                        : "text-white/30"
              }`}
            >
              {node.operational_status
                ?? "NO RUN DATA"}
            </span>
          </div>

          <div className="mt-4 space-y-3 border-t border-white/[0.045] pt-4">
            <InspectorRow
              label="Current runtime"
              value={
                formatDuration(
                  node.current_runtime_seconds,
                )
              }
            />

            <InspectorRow
              label="Expected max"
              value={
                formatDuration(
                  node.expected_max_runtime_seconds,
                )
              }
            />

            <InspectorRow
              label="Runtime basis"
              value={
                node.runtime_threshold_basis
                  ?.replaceAll(
                    "_",
                    " ",
                  )
                ?? "—"
              }
            />

            <InspectorRow
              label="Last success age"
              value={
                node.success_age_hours === null
                  ? "—"
                  : `${node.success_age_hours.toFixed(1)}h`
              }
            />

            <InspectorRow
              label="Success SLA"
              value={
                node.max_success_age_hours === null
                  ? "—"
                  : `${node.max_success_age_hours.toFixed(0)}h`
              }
            />
          </div>

          {node.sla_detail && (
            <p className="mt-4 border-t border-white/[0.045] pt-3 text-[8px] leading-4 text-white/30">
              {node.sla_detail}
            </p>
          )}

          <p className="mt-3 text-[6px] uppercase tracking-[0.1em] text-white/15">
            GridPulse thresholds · not upstream guarantees
          </p>
        </div>
      )}

      {node.source && (
        <div className="mt-3 rounded-xl border border-emerald-300/[0.07] bg-emerald-300/[0.018] p-4">
          <p className="text-[7px] uppercase tracking-[0.13em] text-emerald-200/45">
            Runtime source
          </p>

          <p className="mt-2 font-mono text-[10px] text-white/50">
            {node.source}
          </p>
        </div>
      )}
    </div>
  );
}


function InspectorRow({
  label,
  value,
  mono = false,
  alert = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  alert?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-[7px] uppercase tracking-[0.11em] text-white/20">
        {label}
      </span>

      <span
        className={`text-right text-[8px] ${
          mono
            ? "font-mono"
            : ""
        } ${
          alert
            ? "text-rose-300/80"
            : "text-white/45"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
