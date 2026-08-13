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
          "rgba(255,255,255,0.35)",
        text:
          "text-white/35",
      };
  }
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
            Inspect how public data
            flows through streaming,
            lakehouse transformation,
            analytics modeling,
            serving, and the GridPulse
            intelligence experience.
          </p>
        </div>

        <div className="flex gap-2">
          <div className="rounded-full border border-white/[0.06] bg-black/25 px-3 py-2 text-[8px] text-white/30">
            {
              lineage.nodes.length
            } nodes
          </div>

          <div className="rounded-full border border-amber-300/10 bg-amber-300/[0.025] px-3 py-2 text-[8px] text-amber-200/60">
            {
              degraded
            } degraded
          </div>

          <div className="rounded-full border border-rose-400/10 bg-rose-400/[0.025] px-3 py-2 text-[8px] text-rose-300/60">
            {
              unhealthy
            } unhealthy
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
                  stopOpacity="0.15"
                />

                <stop
                  offset="50%"
                  stopColor="#6ee7b7"
                  stopOpacity="0.55"
                />

                <stop
                  offset="100%"
                  stopColor="#6ee7b7"
                  stopOpacity="0.15"
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
                      stroke="rgba(110,231,183,0.08)"
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
                    className={`relative flex min-w-[74px] flex-col items-center rounded-xl border bg-[#07110e]/95 px-3 py-3 backdrop-blur transition-all duration-300 ${
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
          Public APIs
        </span>

        <span>
          Streaming
        </span>

        <span>
          Lakehouse
        </span>

        <span>
          Analytics
        </span>

        <span>
          Serving
        </span>

        <span>
          Experience
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
      </p>

      <div className="mt-6 rounded-xl border border-white/[0.055] bg-black/20 p-4">
        <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
          Pipeline layer
        </p>

        <p className="mt-2 text-sm text-white/60">
          {node.layer}
        </p>
      </div>

      <div className="mt-3 rounded-xl border border-white/[0.055] bg-black/20 p-4">
        <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
          Current evidence
        </p>

        <p className="mt-2 text-[10px] leading-5 text-white/40">
          {node.detail}
        </p>
      </div>

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
