"use client";

import { Float, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";

function EnergyCore() {
  return (
    <Float
      speed={2}
      rotationIntensity={0.6}
      floatIntensity={1.2}
    >
      <mesh>
        <icosahedronGeometry args={[1.4, 4]} />

        <meshStandardMaterial
          color="#63f5c8"
          emissive="#123f37"
          metalness={0.75}
          roughness={0.2}
          wireframe
        />
      </mesh>

      <mesh scale={0.72}>
        <icosahedronGeometry args={[1.4, 2]} />

        <meshStandardMaterial
          color="#8bdcff"
          emissive="#0b3349"
          metalness={0.5}
          roughness={0.25}
        />
      </mesh>
    </Float>
  );
}

export default function GridCore() {
  return (
    <div className="h-[420px] w-full">
      <Canvas
        camera={{
          position: [0, 0, 5],
          fov: 45,
        }}
      >
        <ambientLight intensity={0.8} />

        <directionalLight
          position={[4, 4, 5]}
          intensity={3}
        />

        <pointLight
          position={[-4, -2, 2]}
          intensity={8}
        />

        <EnergyCore />

        <OrbitControls
          enablePan={false}
          enableZoom={false}
          autoRotate
          autoRotateSpeed={0.8}
        />
      </Canvas>
    </div>
  );
}
