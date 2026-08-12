"use client";

import {
  Html,
  Line,
  Sparkles,
} from "@react-three/drei";
import {
  Canvas,
  useFrame,
} from "@react-three/fiber";
import {
  useMemo,
  useRef,
  useState,
} from "react";
import * as THREE from "three";

type Vec3 = [
  number,
  number,
  number,
];

type NodeKey =
  | "core"
  | "eia"
  | "nws"
  | "afdc"
  | "kafka"
  | "spark"
  | "dbt"
  | "fastapi";

interface GridCoreProps {
  gridObservations: number;
  balancingAuthorities: number;
  evMarkets: number;
  weatherSignals: number;

  topAuthority: string | null;
  topAuthorityPeakDemand: number | null;

  currentTemperatureF: number | null;
  precipitationProbability: number | null;
  currentForecast: string | null;

  topEvCity: string | null;
  topEvStationCount: number | null;
  topEvPortCount: number | null;
}

interface DataNodeProps {
  nodeKey: NodeKey;
  label: string;
  detail: string;
  value?: string;
  position: Vec3;
  color: string;
  active: boolean;
  onSelect: (
    node: NodeKey,
  ) => void;
}

interface ConnectionProps {
  from: Vec3;
  to: Vec3;
  color?: string;
  delay?: number;
}

interface InspectorData {
  eyebrow: string;
  title: string;
  value: string;
  description: string;
  stats: Array<{
    label: string;
    value: string;
  }>;
}

function displayNumber(
  value: number | null,
  suffix = "",
): string {
  if (value === null) {
    return "—";
  }

  return `${new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 1,
    },
  ).format(value)}${suffix}`;
}

function DataNode({
  nodeKey,
  label,
  detail,
  value,
  position,
  color,
  active,
  onSelect,
}: DataNodeProps) {
  const [hovered, setHovered] =
    useState(false);

  const group =
    useRef<THREE.Group>(null);

  const mesh =
    useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (mesh.current) {
      mesh.current.rotation.x +=
        delta * 0.14;

      mesh.current.rotation.y +=
        delta * 0.3;

      const pulse =
        1 +
        Math.sin(
          state.clock.elapsedTime *
            2.2 +
            position[0],
        ) *
          0.035;

      const targetScale =
        active || hovered
          ? 1.2
          : pulse;

      mesh.current.scale.setScalar(
        THREE.MathUtils.lerp(
          mesh.current.scale.x,
          targetScale,
          0.08,
        ),
      );
    }

    if (group.current) {
      const time =
        state.clock.elapsedTime;

      group.current.position.x =
        position[0] +
        Math.sin(
          time * 0.48 +
            position[1],
        ) *
          0.045;

      group.current.position.y =
        position[1] +
        Math.sin(
          time * 0.8 +
            position[0],
        ) *
          0.09;
    }
  });

  return (
    <group
      ref={group}
      position={position}
    >
      <mesh
        ref={mesh}
        onClick={(event) => {
          event.stopPropagation();
          onSelect(nodeKey);
        }}
        onPointerOver={(event) => {
          event.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={() => {
          setHovered(false);
        }}
      >
        <sphereGeometry
          args={[
            0.2,
            32,
            32,
          ]}
        />

        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={
            active
              ? 2.8
              : hovered
                ? 2.3
                : 1.25
          }
          metalness={0.25}
          roughness={0.18}
        />
      </mesh>

      <mesh scale={1.7}>
        <sphereGeometry
          args={[
            0.2,
            24,
            24,
          ]}
        />

        <meshBasicMaterial
          color={color}
          transparent
          opacity={
            active
              ? 0.13
              : hovered
                ? 0.1
                : 0.04
          }
          depthWrite={false}
        />
      </mesh>

      <pointLight
        color={color}
        intensity={
          active
            ? 2.6
            : 0.9
        }
        distance={2}
      />

      <Html
        center
        position={[
          0,
          -0.52,
          0,
        ]}
        distanceFactor={7}
        style={{
          pointerEvents: "auto",
        }}
      >
        <button
          type="button"
          onClick={() => {
            onSelect(nodeKey);
          }}
          className={`
            min-w-[100px]
            cursor-pointer
            rounded-lg
            border
            bg-black/80
            px-2.5
            py-2
            text-center
            backdrop-blur-md
            transition-all
            duration-200
            ${
              active
                ? "border-emerald-300/45 shadow-[0_0_22px_rgba(99,245,200,0.10)]"
                : "border-white/10 hover:border-white/25"
            }
          `}
        >
          <div className="text-[9px] font-semibold tracking-[0.18em] text-white">
            {label}
          </div>

          {value && (
            <div className="mt-1 text-[9px] font-medium text-emerald-200">
              {value}
            </div>
          )}

          <div className="mt-1 text-[6.5px] uppercase tracking-[0.12em] text-white/35">
            {detail}
          </div>
        </button>
      </Html>
    </group>
  );
}

function FlowParticle({
  from,
  to,
  color = "#63f5c8",
  delay = 0,
}: ConnectionProps) {
  const mesh =
    useRef<THREE.Mesh>(null);

  const start = useMemo(
    () =>
      new THREE.Vector3(
        ...from,
      ),
    [from],
  );

  const end = useMemo(
    () =>
      new THREE.Vector3(
        ...to,
      ),
    [to],
  );

  useFrame((state) => {
    if (!mesh.current) {
      return;
    }

    const progress =
      (
        state.clock.elapsedTime *
          0.2 +
        delay
      ) %
      1;

    mesh.current.position.lerpVectors(
      start,
      end,
      progress,
    );

    const pulse =
      0.7 +
      Math.sin(
        progress * Math.PI,
      ) *
        0.7;

    mesh.current.scale.setScalar(
      pulse,
    );
  });

  return (
    <mesh ref={mesh}>
      <sphereGeometry
        args={[
          0.04,
          12,
          12,
        ]}
      />

      <meshBasicMaterial
        color={color}
      />

      <pointLight
        color={color}
        intensity={0.65}
        distance={0.5}
      />
    </mesh>
  );
}

function Connection({
  from,
  to,
  color = "#63f5c8",
  delay = 0,
}: ConnectionProps) {
  return (
    <>
      <Line
        points={[
          from,
          to,
        ]}
        color={color}
        transparent
        opacity={0.2}
        lineWidth={1}
      />

      <FlowParticle
        from={from}
        to={to}
        color={color}
        delay={delay}
      />

      <FlowParticle
        from={from}
        to={to}
        color={color}
        delay={delay + 0.5}
      />
    </>
  );
}

function makeEllipse(
  radiusX: number,
  radiusY: number,
): Vec3[] {
  const points: Vec3[] = [];

  for (
    let index = 0;
    index <= 180;
    index += 1
  ) {
    const angle =
      (index / 180) *
      Math.PI *
      2;

    points.push([
      Math.cos(angle) *
        radiusX,
      Math.sin(angle) *
        radiusY,
      0,
    ]);
  }

  return points;
}

function OrbitRings() {
  const root =
    useRef<THREE.Group>(null);

  const wideOrbit =
    useMemo(
      () =>
        makeEllipse(
          3.35,
          1.52,
        ),
      [],
    );

  const mediumOrbit =
    useMemo(
      () =>
        makeEllipse(
          2.9,
          1.8,
        ),
      [],
    );

  const tallOrbit =
    useMemo(
      () =>
        makeEllipse(
          2.4,
          2,
        ),
      [],
    );

  useFrame((_, delta) => {
    if (!root.current) {
      return;
    }

    root.current.rotation.z +=
      delta * 0.018;
  });

  return (
    <group ref={root}>
      <group
        rotation={[
          0.14,
          0.22,
          0.08,
        ]}
      >
        <Line
          points={wideOrbit}
          color="#155246"
          transparent
          opacity={0.5}
          lineWidth={1}
        />
      </group>

      <group
        rotation={[
          -0.18,
          0.32,
          -0.44,
        ]}
      >
        <Line
          points={wideOrbit}
          color="#155246"
          transparent
          opacity={0.43}
          lineWidth={1}
        />
      </group>

      <group
        rotation={[
          0.42,
          -0.18,
          0.68,
        ]}
      >
        <Line
          points={mediumOrbit}
          color="#155246"
          transparent
          opacity={0.38}
          lineWidth={1}
        />
      </group>

      <group
        rotation={[
          -0.38,
          -0.24,
          1.02,
        ]}
      >
        <Line
          points={tallOrbit}
          color="#155246"
          transparent
          opacity={0.34}
          lineWidth={1}
        />
      </group>
    </group>
  );
}

interface IntelligenceCoreProps {
  authorityCount: number;
  active: boolean;
  onSelect: (
    node: NodeKey,
  ) => void;
}

function IntelligenceCore({
  authorityCount,
  active,
  onSelect,
}: IntelligenceCoreProps) {
  const outer =
    useRef<THREE.Mesh>(null);

  const middle =
    useRef<THREE.Mesh>(null);

  const inner =
    useRef<THREE.Mesh>(null);

  const glow =
    useRef<THREE.Mesh>(null);

  const [hovered, setHovered] =
    useState(false);

  useFrame((state, delta) => {
    if (outer.current) {
      outer.current.rotation.x +=
        delta * 0.08;

      outer.current.rotation.y +=
        delta * 0.16;
    }

    if (middle.current) {
      middle.current.rotation.x -=
        delta * 0.13;

      middle.current.rotation.z +=
        delta * 0.1;
    }

    if (inner.current) {
      const pulse =
        1 +
        Math.sin(
          state.clock.elapsedTime *
            1.8,
        ) *
          0.045;

      inner.current.scale.setScalar(
        pulse,
      );
    }

    if (glow.current) {
      const pulse =
        1.08 +
        Math.sin(
          state.clock.elapsedTime *
            1.3,
        ) *
          0.04;

      glow.current.scale.setScalar(
        pulse,
      );
    }
  });

  return (
    <group>
      <OrbitRings />

      {/* Soft outer glow */}
      <mesh
        ref={glow}
        scale={1.08}
      >
        <sphereGeometry
          args={[
            1,
            48,
            48,
          ]}
        />

        <meshBasicMaterial
          color="#63f5c8"
          transparent
          opacity={0.055}
          depthWrite={false}
        />
      </mesh>

      {/* Large luminous inner ball */}
      <mesh
        ref={inner}
        scale={0.91}
      >
        <sphereGeometry
          args={[
            1,
            64,
            64,
          ]}
        />

        <meshStandardMaterial
          color="#eafff9"
          emissive="#9fffe6"
          emissiveIntensity={1.65}
          roughness={0.18}
          metalness={0.05}
        />
      </mesh>

      {/* Main triangular wireframe */}
      <mesh
        ref={outer}
        onClick={(event) => {
          event.stopPropagation();
          onSelect("core");
        }}
        onPointerOver={(event) => {
          event.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={() => {
          setHovered(false);
        }}
      >
        <icosahedronGeometry
          args={[
            1.02,
            3,
          ]}
        />

        <meshStandardMaterial
          color="#38d9ae"
          emissive="#0c6d58"
          emissiveIntensity={
            active || hovered
              ? 2
              : 1.25
          }
          metalness={0.72}
          roughness={0.2}
          wireframe
          transparent
          opacity={0.84}
        />
      </mesh>

      {/* Second fine rotating wireframe */}
      <mesh
        ref={middle}
        scale={0.985}
      >
        <icosahedronGeometry
          args={[
            1,
            2,
          ]}
        />

        <meshStandardMaterial
          color="#64f5c8"
          emissive="#174b3f"
          emissiveIntensity={1}
          wireframe
          transparent
          opacity={0.28}
        />
      </mesh>

      <pointLight
        color="#63f5c8"
        intensity={
          active ? 11 : 8
        }
        distance={5}
      />

      <pointLight
        position={[
          0.65,
          0.8,
          1.4,
        ]}
        color="#ffffff"
        intensity={5}
        distance={3}
      />

      <Html
        center
        position={[
          0,
          -1.42,
          0,
        ]}
        distanceFactor={8}
        style={{
          pointerEvents: "auto",
        }}
      >
        <button
          type="button"
          onClick={() => {
            onSelect("core");
          }}
          className="cursor-pointer whitespace-nowrap text-center"
        >
          <div className="text-[9px] font-semibold tracking-[0.24em] text-emerald-200">
            GRIDPULSE CORE
          </div>

          <div className="mt-1 text-[9px] font-medium text-white/65">
            {authorityCount}
          </div>

          <div className="mt-1 text-[6.5px] uppercase tracking-[0.14em] text-white/30">
            Balancing authorities
          </div>
        </button>
      </Html>
    </group>
  );
}

interface NetworkSceneProps {
  gridObservations: number;
  balancingAuthorities: number;
  evMarkets: number;
  weatherSignals: number;
  selectedNode: NodeKey;
  onSelect: (
    node: NodeKey,
  ) => void;
}

function NetworkScene({
  gridObservations,
  balancingAuthorities,
  evMarkets,
  weatherSignals,
  selectedNode,
  onSelect,
}: NetworkSceneProps) {
  const eia: Vec3 = [
    -3.5,
    1.5,
    0,
  ];

  const nws: Vec3 = [
    -3.8,
    0,
    0,
  ];

  const afdc: Vec3 = [
    -3.5,
    -1.5,
    0,
  ];

  const core: Vec3 = [
    0,
    0,
    0,
  ];

  const kafka: Vec3 = [
    2.55,
    1.5,
    0,
  ];

  const spark: Vec3 = [
    3.35,
    0.5,
    0,
  ];

  const dbt: Vec3 = [
    3.35,
    -0.5,
    0,
  ];

  const api: Vec3 = [
    2.55,
    -1.5,
    0,
  ];

  return (
    <>
      <ambientLight
        intensity={0.38}
      />

      <directionalLight
        position={[
          4,
          5,
          7,
        ]}
        intensity={1.7}
      />

      <Sparkles
        count={65}
        scale={[
          8.5,
          5,
          2,
        ]}
        size={1}
        speed={0.15}
        opacity={0.24}
        color="#63f5c8"
      />

      <Connection
        from={eia}
        to={core}
        color="#63f5c8"
        delay={0}
      />

      <Connection
        from={nws}
        to={core}
        color="#8bdcff"
        delay={0.17}
      />

      <Connection
        from={afdc}
        to={core}
        color="#d5f77d"
        delay={0.34}
      />

      <Connection
        from={core}
        to={kafka}
        color="#63f5c8"
        delay={0.12}
      />

      <Connection
        from={kafka}
        to={spark}
        color="#8bdcff"
        delay={0.3}
      />

      <Connection
        from={spark}
        to={dbt}
        color="#a78bfa"
        delay={0.48}
      />

      <Connection
        from={dbt}
        to={api}
        color="#f0abfc"
        delay={0.66}
      />

      <DataNode
        nodeKey="eia"
        label="EIA"
        value={`${gridObservations}`}
        detail="Grid observations"
        position={eia}
        color="#63f5c8"
        active={
          selectedNode === "eia"
        }
        onSelect={onSelect}
      />

      <DataNode
        nodeKey="nws"
        label="NWS"
        value={`${weatherSignals}`}
        detail="Weather signals"
        position={nws}
        color="#8bdcff"
        active={
          selectedNode === "nws"
        }
        onSelect={onSelect}
      />

      <DataNode
        nodeKey="afdc"
        label="AFDC"
        value={`${evMarkets}`}
        detail="EV markets"
        position={afdc}
        color="#d5f77d"
        active={
          selectedNode === "afdc"
        }
        onSelect={onSelect}
      />

      <IntelligenceCore
        authorityCount={
          balancingAuthorities
        }
        active={
          selectedNode === "core"
        }
        onSelect={onSelect}
      />

      <DataNode
        nodeKey="kafka"
        label="KAFKA"
        detail="Streaming"
        position={kafka}
        color="#63f5c8"
        active={
          selectedNode === "kafka"
        }
        onSelect={onSelect}
      />

      <DataNode
        nodeKey="spark"
        label="SPARK"
        detail="Bronze · Silver · Gold"
        position={spark}
        color="#8bdcff"
        active={
          selectedNode === "spark"
        }
        onSelect={onSelect}
      />

      <DataNode
        nodeKey="dbt"
        label="DBT"
        detail="Analytics marts"
        position={dbt}
        color="#a78bfa"
        active={
          selectedNode === "dbt"
        }
        onSelect={onSelect}
      />

      <DataNode
        nodeKey="fastapi"
        label="FASTAPI"
        detail="Serving layer"
        position={api}
        color="#f0abfc"
        active={
          selectedNode ===
          "fastapi"
        }
        onSelect={onSelect}
      />
    </>
  );
}

function Inspector({
  data,
}: {
  data: InspectorData;
}) {
  return (
    <div className="mx-auto grid w-[94%] gap-3 rounded-xl border border-white/[0.08] bg-black/35 px-4 py-3 backdrop-blur-xl md:grid-cols-[1fr_auto] md:items-center">
      <div>
        <p className="text-[8px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
          {data.eyebrow}
        </p>

        <div className="mt-1.5 flex items-baseline gap-2">
          <h3 className="text-sm font-medium text-white">
            {data.title}
          </h3>

          <span className="text-base font-light text-emerald-200">
            {data.value}
          </span>
        </div>

        <p className="mt-1 max-w-[430px] text-[9px] leading-4 text-white/35">
          {data.description}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {data.stats.map(
          (stat) => (
            <div
              key={stat.label}
              className="min-w-[82px] rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-2"
            >
              <p className="text-[7px] uppercase tracking-[0.12em] text-white/25">
                {stat.label}
              </p>

              <p className="mt-1 text-[10px] font-medium text-white/65">
                {stat.value}
              </p>
            </div>
          ),
        )}
      </div>
    </div>
  );
}

export default function GridCore({
  gridObservations,
  balancingAuthorities,
  evMarkets,
  weatherSignals,
  topAuthority,
  topAuthorityPeakDemand,
  currentTemperatureF,
  precipitationProbability,
  currentForecast,
  topEvCity,
  topEvStationCount,
  topEvPortCount,
}: GridCoreProps) {
  const [
    selectedNode,
    setSelectedNode,
  ] = useState<NodeKey>("core");

  const inspectorData: Record<
    NodeKey,
    InspectorData
  > = {
    core: {
      eyebrow:
        "INTELLIGENCE CORE",
      title:
        "GridPulse",
      value:
        `${balancingAuthorities}`,
      description:
        "Public-source ingestion, streaming, transformation, analytics, serving, and observability connected through one intelligence platform.",
      stats: [
        {
          label:
            "Sources",
          value: "3",
        },
        {
          label:
            "Authorities",
          value:
            `${balancingAuthorities}`,
        },
        {
          label:
            "Grid rows",
          value:
            `${gridObservations}`,
        },
      ],
    },

    eia: {
      eyebrow:
        "EIA GRID DATA",
      title:
        topAuthority ??
        "Electricity intelligence",
      value:
        `${gridObservations}`,
      description:
        "Electricity observations transformed into balancing-authority demand, generation, interchange, and forecast analytics.",
      stats: [
        {
          label:
            "Rows",
          value:
            `${gridObservations}`,
        },
        {
          label:
            "Authorities",
          value:
            `${balancingAuthorities}`,
        },
        {
          label:
            "Peak",
          value:
            displayNumber(
              topAuthorityPeakDemand,
              " MWh",
            ),
        },
      ],
    },

    nws: {
      eyebrow:
        "NWS WEATHER",
      title:
        currentForecast ??
        "Weather signal",
      value:
        displayNumber(
          currentTemperatureF,
          "°F",
        ),
      description:
        "Hourly weather forecast signals providing environmental context to GridPulse analytics.",
      stats: [
        {
          label:
            "Signals",
          value:
            `${weatherSignals}`,
        },
        {
          label:
            "Temp",
          value:
            displayNumber(
              currentTemperatureF,
              "°F",
            ),
        },
        {
          label:
            "Precip",
          value:
            displayNumber(
              precipitationProbability,
              "%",
            ),
        },
      ],
    },

    afdc: {
      eyebrow:
        "AFDC EV NETWORK",
      title:
        topEvCity ??
        "EV infrastructure",
      value:
        `${evMarkets}`,
      description:
        "Charging-station records aggregated into city-level EV infrastructure intelligence.",
      stats: [
        {
          label:
            "Markets",
          value:
            `${evMarkets}`,
        },
        {
          label:
            "Stations",
          value:
            displayNumber(
              topEvStationCount,
            ),
        },
        {
          label:
            "Ports",
          value:
            displayNumber(
              topEvPortCount,
            ),
        },
      ],
    },

    kafka: {
      eyebrow:
        "EVENT STREAMING",
      title:
        "Apache Kafka",
      value:
        "LIVE",
      description:
        "Canonical GridPulse events with replay metadata, manual offsets, and dead-letter handling.",
      stats: [
        {
          label:
            "Sources",
          value: "3",
        },
        {
          label:
            "DLQ",
          value:
            "Enabled",
        },
        {
          label:
            "Offsets",
          value:
            "Manual",
        },
      ],
    },

    spark: {
      eyebrow:
        "STREAM PROCESSING",
      title:
        "Apache Spark",
      value:
        "3 layers",
      description:
        "Bronze, Silver, and Gold processing with quality validation and deduplication.",
      stats: [
        {
          label:
            "Bronze",
          value:
            "Raw",
        },
        {
          label:
            "Silver",
          value:
            "Typed",
        },
        {
          label:
            "Gold",
          value:
            "Analytics",
        },
      ],
    },

    dbt: {
      eyebrow:
        "ANALYTICS ENGINEERING",
      title:
        "dbt + DuckDB",
      value:
        "4 marts",
      description:
        "Tested analytical marts exposed through the local DuckDB serving warehouse.",
      stats: [
        {
          label:
            "Grid",
          value:
            `${gridObservations}`,
        },
        {
          label:
            "EV",
          value:
            `${evMarkets}`,
        },
        {
          label:
            "Weather",
          value:
            `${weatherSignals}`,
        },
      ],
    },

    fastapi: {
      eyebrow:
        "SERVING LAYER",
      title:
        "FastAPI",
      value:
        "ONLINE",
      description:
        "Typed read-only APIs serving GridPulse intelligence to the Next.js frontend.",
      stats: [
        {
          label:
            "Warehouse",
          value:
            "DuckDB",
        },
        {
          label:
            "Metrics",
          value:
            "Prometheus",
        },
        {
          label:
            "UI",
          value:
            "Next.js",
        },
      ],
    },
  };

  return (
    <div className="w-full">
      <div className="h-[455px] w-full overflow-hidden">
        <Canvas
          camera={{
            position: [
              0,
              0,
              9,
            ],
            fov: 48,
          }}
          dpr={[
            1,
            1.75,
          ]}
        >
          <NetworkScene
            gridObservations={
              gridObservations
            }
            balancingAuthorities={
              balancingAuthorities
            }
            evMarkets={
              evMarkets
            }
            weatherSignals={
              weatherSignals
            }
            selectedNode={
              selectedNode
            }
            onSelect={
              setSelectedNode
            }
          />
        </Canvas>
      </div>

      <div className="mt-4">
        <Inspector
          data={
            inspectorData[
              selectedNode
            ]
          }
        />
      </div>
    </div>
  );
}
