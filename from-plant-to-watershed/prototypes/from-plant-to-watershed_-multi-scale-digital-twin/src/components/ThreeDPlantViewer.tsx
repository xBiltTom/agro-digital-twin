/**
 * Level 1 & 2: 3D Functional-Structural Plant Model (FSPM) & Field Aggregation Viewer
 * Three.js WebGL procedural rendering of Zea mays L. root-canopy architecture and stratified soil horizons.
 */

import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { PlantArchitecture } from '../types/scientific';
import { simulateFspmPlant } from '../services/scientificEngine';
import {
  Maximize2,
  Minimize2,
  Layers,
  Activity,
  Eye,
  RotateCcw,
  Sparkles,
  Info,
  Droplets,
  Thermometer,
  ShieldCheck,
  Grid3X3,
} from 'lucide-react';

interface ThreeDPlantViewerProps {
  currentDay?: number;
  tempDelta?: number;
  waterStress?: number;
  isSorghum?: boolean;
}

export const ThreeDPlantViewer: React.FC<ThreeDPlantViewerProps> = ({
  currentDay = 65,
  tempDelta = 0,
  waterStress = 0.92,
  isSorghum = false,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [day, setDay] = useState<number>(currentDay);
  const [viewMode, setViewMode] = useState<'both' | 'canopy' | 'roots' | 'field'>('both');
  const [showStressHeatmap, setShowStressHeatmap] = useState<boolean>(true);
  const [animateXylemFlux, setAnimateXylemFlux] = useState<boolean>(true);
  const [selectedOrgan, setSelectedOrgan] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  // Synchronize day if prop updates
  useEffect(() => {
    setDay(currentDay);
  }, [currentDay]);

  const plantData: PlantArchitecture = simulateFspmPlant(day, tempDelta, waterStress, isSorghum);

  // References for Three.js state
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const plantGroupRef = useRef<THREE.Group | null>(null);
  const soilGroupRef = useRef<THREE.Group | null>(null);
  const fieldGroupRef = useRef<THREE.Group | null>(null);
  const xylemParticlesRef = useRef<THREE.Points | null>(null);

  // Initialize Three.js scene
  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x0a101d);
    scene.fog = new THREE.FogExp2(0x0a101d, 0.015);

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 8, 30);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 1.4);
    sunLight.position.set(15, 30, 20);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 1024;
    sunLight.shadow.mapSize.height = 1024;
    scene.add(sunLight);

    const subsoilLight = new THREE.DirectionalLight(0x7395ae, 0.4);
    subsoilLight.position.set(-10, -20, -10);
    scene.add(subsoilLight);

    // Groups
    const plantGroup = new THREE.Group();
    plantGroupRef.current = plantGroup;
    scene.add(plantGroup);

    const soilGroup = new THREE.Group();
    soilGroupRef.current = soilGroup;
    scene.add(soilGroup);

    const fieldGroup = new THREE.Group();
    fieldGroupRef.current = fieldGroup;
    scene.add(fieldGroup);

    // Orbit controls simulation via mouse drag
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let rotY = 0;
    let rotX = 0.1;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      rotY += deltaX * 0.008;
      rotX += deltaY * 0.008;
      rotX = Math.max(-0.6, Math.min(0.8, rotX));
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (!cameraRef.current) return;
      cameraRef.current.position.z += e.deltaY * 0.02;
      cameraRef.current.position.z = Math.max(10, Math.min(65, cameraRef.current.position.z));
    };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    domElem.addEventListener('wheel', onWheel, { passive: false });

    // Render loop
    let clock = new THREE.Clock();
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth camera orbit
      if (cameraRef.current) {
        const radius = cameraRef.current.position.z;
        cameraRef.current.position.x = radius * Math.sin(rotY) * Math.cos(rotX);
        cameraRef.current.position.y = 8 + radius * Math.sin(rotX);
        cameraRef.current.position.z = radius * Math.cos(rotY) * Math.cos(rotX);
        cameraRef.current.lookAt(0, 3, 0);
      }

      // Xylem flux particle pulse
      if (xylemParticlesRef.current && animateXylemFlux) {
        const positions = xylemParticlesRef.current.geometry.attributes.position.array as Float32Array;
        for (let i = 1; i < positions.length; i += 3) {
          positions[i] += 0.05;
          if (positions[i] > 16) {
            positions[i] = -8;
          }
        }
        xylemParticlesRef.current.geometry.attributes.position.needsUpdate = true;
      }

      renderer.render(scene, camera);
    };
    animate();

    // Resize observer
    const handleResize = () => {
      if (!container || !cameraRef.current || !rendererRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      domElem.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      domElem.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    };
  }, []);

  // Re-build 3D Meshes when day, viewMode, waterStress, or isSorghum changes
  useEffect(() => {
    if (!sceneRef.current || !plantGroupRef.current || !soilGroupRef.current || !fieldGroupRef.current) return;

    const plantGroup = plantGroupRef.current;
    const soilGroup = soilGroupRef.current;
    const fieldGroup = fieldGroupRef.current;

    // Clear previous geometries
    while (plantGroup.children.length > 0) {
      const obj = plantGroup.children[0];
      plantGroup.remove(obj);
    }
    while (soilGroup.children.length > 0) {
      const obj = soilGroup.children[0];
      soilGroup.remove(obj);
    }
    while (fieldGroup.children.length > 0) {
      const obj = fieldGroup.children[0];
      fieldGroup.remove(obj);
    }

    const currentPlant = simulateFspmPlant(day, tempDelta, waterStress, isSorghum);

    // Colors according to water stress factor
    const stressVal = currentPlant.waterStressFactor;
    const canopyColor = showStressHeatmap
      ? new THREE.Color().setHSL(0.33 * stressVal, 0.85, 0.42 + 0.1 * (1 - stressVal))
      : new THREE.Color(0x2e7d32);

    const rootColor = showStressHeatmap
      ? new THREE.Color().setHSL(0.12 * stressVal, 0.7, 0.5)
      : new THREE.Color(0xdfba73);

    // ==========================================
    // 1. SOIL STRATIFIED HORIZONS (Ground plane at y = 0)
    // ==========================================
    if (viewMode === 'both' || viewMode === 'roots') {
      // Surface Ground Grid
      const groundGrid = new THREE.GridHelper(24, 24, 0x4a5568, 0x1f2937);
      groundGrid.position.y = 0;
      soilGroup.add(groundGrid);

      // Topsoil horizon Ap (0 - 20 cm => y from 0 to -2.0)
      const topsoilGeo = new THREE.BoxGeometry(22, 2.0, 22);
      const topsoilMat = new THREE.MeshStandardMaterial({
        color: 0x3d2b1f,
        transparent: true,
        opacity: 0.35,
        wireframe: false,
      });
      const topsoilMesh = new THREE.Mesh(topsoilGeo, topsoilMat);
      topsoilMesh.position.y = -1.0;
      soilGroup.add(topsoilMesh);

      // Subsoil horizon Bw (20 - 65 cm => y from -2.0 to -6.5)
      const subsoilGeo = new THREE.BoxGeometry(22, 4.5, 22);
      const subsoilMat = new THREE.MeshStandardMaterial({
        color: 0x5c4033,
        transparent: true,
        opacity: 0.25,
      });
      const subsoilMesh = new THREE.Mesh(subsoilGeo, subsoilMat);
      subsoilMesh.position.y = -4.25;
      soilGroup.add(subsoilMesh);

      // Deep horizon C (65 - 150 cm => y from -6.5 to -15.0)
      const deepSoilGeo = new THREE.BoxGeometry(22, 8.5, 22);
      const deepSoilMat = new THREE.MeshStandardMaterial({
        color: 0x7a5c43,
        transparent: true,
        opacity: 0.18,
      });
      const deepSoilMesh = new THREE.Mesh(deepSoilGeo, deepSoilMat);
      deepSoilMesh.position.y = -10.75;
      soilGroup.add(deepSoilMesh);

      // Depth tick markers (text markers simulated via colored small cylinders)
      [-2, -6.5, -15].forEach((yPos) => {
        const markerGeo = new THREE.RingGeometry(11, 11.1, 32);
        const markerMat = new THREE.MeshBasicMaterial({ color: 0x64748b, side: THREE.DoubleSide });
        const marker = new THREE.Mesh(markerGeo, markerMat);
        marker.rotation.x = Math.PI / 2;
        marker.position.y = yPos;
        soilGroup.add(marker);
      });
    }

    // ==========================================
    // 2. FSPM INDIVIDUAL PLANT (Level 1)
    // ==========================================
    if (viewMode !== 'field') {
      const scaleHeight = currentPlant.plantHeightCm / 15; // 0 to ~15 units
      const stemRadius = 0.18 * (day / 80 + 0.3);

      // --- STEM (Phytomer segments) ---
      if (viewMode === 'both' || viewMode === 'canopy') {
        const stemHeight = Math.max(0.4, scaleHeight);
        const stemGeo = new THREE.CylinderGeometry(stemRadius * 0.7, stemRadius, stemHeight, 16);
        const stemMat = new THREE.MeshStandardMaterial({
          color: canopyColor,
          roughness: 0.4,
          metalness: 0.1,
        });
        const stemMesh = new THREE.Mesh(stemGeo, stemMat);
        stemMesh.position.y = stemHeight / 2;
        stemMesh.castShadow = true;
        plantGroup.add(stemMesh);

        // --- LEAVES (Arching Curved Ribbons) ---
        const leafCount = currentPlant.leafCount;
        for (let i = 0; i < leafCount; i++) {
          const leafStageFraction = i / leafCount;
          const nodeY = (leafStageFraction * 0.85 + 0.1) * stemHeight;
          const leafAngle = i * (Math.PI * 0.618033); // Golden angle phyllotaxis
          const leafLen = Math.max(1.2, 5.5 * Math.sin(leafStageFraction * Math.PI) * (day / 80));

          // Curved leaf spline
          const p0 = new THREE.Vector3(0, 0, 0);
          const p1 = new THREE.Vector3(
            Math.cos(leafAngle) * leafLen * 0.4,
            leafLen * 0.25,
            Math.sin(leafAngle) * leafLen * 0.4
          );
          const p2 = new THREE.Vector3(
            Math.cos(leafAngle) * leafLen * 0.85,
            0.0,
            Math.sin(leafAngle) * leafLen * 0.85
          );
          const p3 = new THREE.Vector3(
            Math.cos(leafAngle) * leafLen,
            -leafLen * 0.35,
            Math.sin(leafAngle) * leafLen
          );

          const curve = new THREE.CubicBezierCurve3(p0, p1, p2, p3);
          const tubeGeo = new THREE.TubeGeometry(curve, 12, 0.08 * (1 - leafStageFraction * 0.4), 6, false);
          const leafMat = new THREE.MeshStandardMaterial({
            color: canopyColor,
            roughness: 0.3,
            side: THREE.DoubleSide,
          });
          const leafMesh = new THREE.Mesh(tubeGeo, leafMat);
          leafMesh.position.y = nodeY;
          leafMesh.castShadow = true;
          plantGroup.add(leafMesh);

          // Leaf blade lamina (flat plane expansion)
          const bladePoints = curve.getPoints(8);
          for (let b = 1; b < bladePoints.length - 1; b++) {
            const width = 0.35 * Math.sin((b / bladePoints.length) * Math.PI);
            const pt = bladePoints[b];
            const bladeGeo = new THREE.SphereGeometry(width, 4, 4);
            bladeGeo.scale(1, 0.1, 0.5);
            const bladeMesh = new THREE.Mesh(bladeGeo, leafMat);
            bladeMesh.position.set(pt.x, nodeY + pt.y, pt.z);
            bladeMesh.rotation.y = leafAngle;
            plantGroup.add(bladeMesh);
          }
        }

        // --- TASSEL / COB at Reproductive Stage ---
        if (day >= 85) {
          // Tassel at apex
          const tasselGeo = new THREE.ConeGeometry(0.3, 1.8, 8);
          const tasselMat = new THREE.MeshStandardMaterial({ color: 0xd4af37 });
          const tasselMesh = new THREE.Mesh(tasselGeo, tasselMat);
          tasselMesh.position.y = stemHeight + 0.9;
          plantGroup.add(tasselMesh);

          // Ear of Corn / Sorghum head
          const cobGeo = new THREE.CylinderGeometry(0.35, 0.4, 2.2, 8);
          const cobMat = new THREE.MeshStandardMaterial({ color: isSorghum ? 0x8b3a3a : 0xe6b800 });
          const cobMesh = new THREE.Mesh(cobGeo, cobMat);
          cobMesh.position.set(0.4, stemHeight * 0.55, 0.2);
          cobMesh.rotation.z = -0.4;
          plantGroup.add(cobMesh);
        }
      }

      // --- ROOTS (Stratified architecture below ground y = 0) ---
      if (viewMode === 'both' || viewMode === 'roots') {
        const rootDepthUnits = (currentPlant.maxRootDepthCm / 150) * 14; // up to 14 units deep

        // 1. Primary Taproot descending vertically
        const taprootCurve = new THREE.CatmullRomCurve3([
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(0.05, -rootDepthUnits * 0.25, 0.02),
          new THREE.Vector3(-0.08, -rootDepthUnits * 0.6, -0.05),
          new THREE.Vector3(0.02, -rootDepthUnits, 0.0),
        ]);
        const taprootGeo = new THREE.TubeGeometry(taprootCurve, 18, stemRadius * 0.75, 8, false);
        const rootMat = new THREE.MeshStandardMaterial({
          color: rootColor,
          roughness: 0.8,
        });
        const taprootMesh = new THREE.Mesh(taprootGeo, rootMat);
        plantGroup.add(taprootMesh);

        // 2. Seminal and Crown Roots branching outward
        const crownCount = currentPlant.rootArchitecture.crownRootCount;
        for (let r = 0; r < crownCount; r++) {
          const angle = (r / crownCount) * Math.PI * 2;
          const spread = 1.2 + 2.0 * Math.sin(r);
          const depth = Math.min(rootDepthUnits * 0.85, 2.0 + (r / crownCount) * 8);

          const rCurve = new THREE.CubicBezierCurve3(
            new THREE.Vector3(0, -0.2, 0),
            new THREE.Vector3(Math.cos(angle) * spread * 0.5, -depth * 0.3, Math.sin(angle) * spread * 0.5),
            new THREE.Vector3(Math.cos(angle) * spread, -depth * 0.7, Math.sin(angle) * spread),
            new THREE.Vector3(Math.cos(angle) * spread * 1.3, -depth, Math.sin(angle) * spread * 1.3)
          );
          const rGeo = new THREE.TubeGeometry(rCurve, 12, 0.06, 6, false);
          const rMesh = new THREE.Mesh(rGeo, rootMat);
          plantGroup.add(rMesh);

          // Lateral tertiary branches
          if (day > 40 && r % 2 === 0) {
            const latCurve = new THREE.LineCurve3(
              rCurve.getPoint(0.5),
              new THREE.Vector3(
                rCurve.getPoint(0.5).x + Math.cos(angle + 0.8) * 0.8,
                rCurve.getPoint(0.5).y - 0.6,
                rCurve.getPoint(0.5).z + Math.sin(angle + 0.8) * 0.8
              )
            );
            const latGeo = new THREE.TubeGeometry(latCurve, 6, 0.03, 4, false);
            const latMesh = new THREE.Mesh(latGeo, rootMat);
            plantGroup.add(latMesh);
          }
        }
      }

      // --- XYLEM FLUX STREAMING PARTICLES ---
      if (animateXylemFlux) {
        const particleCount = 120;
        const partGeo = new THREE.BufferGeometry();
        const posArray = new Float32Array(particleCount * 3);

        for (let p = 0; p < particleCount; p++) {
          const y = -8 + Math.random() * 22;
          const r = 0.12 * Math.random();
          const theta = Math.random() * Math.PI * 2;
          posArray[p * 3] = Math.cos(theta) * r;
          posArray[p * 3 + 1] = y;
          posArray[p * 3 + 2] = Math.sin(theta) * r;
        }
        partGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
        const partMat = new THREE.PointsMaterial({
          color: 0x38bdf8,
          size: 0.18,
          transparent: true,
          opacity: 0.8,
        });
        const particles = new THREE.Points(partGeo, partMat);
        xylemParticlesRef.current = particles;
        plantGroup.add(particles);
      }
    }

    // ==========================================
    // 3. FIELD AGGREGATION VIEW (Level 2: ~1000 plants in 3D grid)
    // ==========================================
    if (viewMode === 'field') {
      const rows = 28;
      const cols = 35; // ~980 plants
      const spacingX = 0.75;
      const spacingZ = 0.75;

      const instancedStemGeo = new THREE.CylinderGeometry(0.04, 0.06, 1.8, 6);
      const instancedLeafGeo = new THREE.ConeGeometry(0.22, 1.4, 4);

      const fieldStemMesh = new THREE.InstancedMesh(
        instancedStemGeo,
        new THREE.MeshStandardMaterial({ color: canopyColor }),
        rows * cols
      );
      const fieldLeafMesh = new THREE.InstancedMesh(
        instancedLeafGeo,
        new THREE.MeshStandardMaterial({ color: canopyColor }),
        rows * cols
      );

      const dummy = new THREE.Object3D();
      let idx = 0;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const posX = (c - cols / 2) * spacingX;
          const posZ = (r - rows / 2) * spacingZ;
          // Micro-topographic undulation
          const posY = Math.sin(posX * 0.15) * Math.cos(posZ * 0.15) * 0.4;

          // Slight random growth variance
          const scaleVar = 0.75 + Math.random() * 0.5;

          dummy.position.set(posX, posY + 0.9 * scaleVar, posZ);
          dummy.scale.set(scaleVar, scaleVar, scaleVar);
          dummy.updateMatrix();
          fieldStemMesh.setMatrixAt(idx, dummy.matrix);

          dummy.position.set(posX, posY + 1.6 * scaleVar, posZ);
          dummy.rotation.x = 0.15 * Math.sin(idx);
          dummy.updateMatrix();
          fieldLeafMesh.setMatrixAt(idx, dummy.matrix);

          idx++;
        }
      }

      fieldStemMesh.instanceMatrix.needsUpdate = true;
      fieldLeafMesh.instanceMatrix.needsUpdate = true;
      fieldGroup.add(fieldStemMesh);
      fieldGroup.add(fieldLeafMesh);

      // Soil ground plane
      const fieldGroundGeo = new THREE.PlaneGeometry(cols * spacingX + 4, rows * spacingZ + 4);
      const fieldGroundMat = new THREE.MeshStandardMaterial({ color: 0x3d2b1f });
      const fieldGround = new THREE.Mesh(fieldGroundGeo, fieldGroundMat);
      fieldGround.rotation.x = -Math.PI / 2;
      fieldGround.position.y = 0;
      fieldGroup.add(fieldGround);
    }
  }, [day, viewMode, showStressHeatmap, animateXylemFlux, waterStress, tempDelta, isSorghum]);

  const resetCamera = () => {
    if (!cameraRef.current) return;
    cameraRef.current.position.set(0, 8, 30);
    cameraRef.current.lookAt(0, 3, 0);
  };

  return (
    <div
      id="fspm-3d-module-container"
      className={`relative bg-slate-950 rounded-xl border border-slate-800 overflow-hidden flex flex-col transition-all duration-300 ${
        isFullscreen ? 'fixed inset-2 z-50 shadow-2xl' : 'w-full h-[540px]'
      }`}
    >
      {/* Viewport Top Header Bar */}
      <div className="absolute top-0 left-0 right-0 z-10 p-3 bg-gradient-to-b from-slate-950/90 to-transparent flex items-center justify-between pointer-events-none">
        <div className="pointer-events-auto flex items-center gap-2">
          <span className="px-2.5 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold rounded-md flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            {viewMode === 'field' ? 'Level 2: Field Aggregation (~1000 Plants)' : 'Level 1: 3D FSPM Architecture'}
          </span>
          <span className="px-2 py-0.5 bg-slate-800/80 text-slate-300 text-xs rounded border border-slate-700">
            {isSorghum ? 'Sorghum bicolor L.' : 'Zea mays L.'} (Stage: {plantData.growthStage})
          </span>
        </div>

        {/* View Mode Selector Tabs */}
        <div className="pointer-events-auto flex items-center bg-slate-900/90 backdrop-blur p-1 rounded-lg border border-slate-700 text-xs">
          <button
            id="view-both-btn"
            onClick={() => setViewMode('both')}
            className={`px-2.5 py-1 rounded transition ${
              viewMode === 'both' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            Plant & Soil
          </button>
          <button
            id="view-canopy-btn"
            onClick={() => setViewMode('canopy')}
            className={`px-2.5 py-1 rounded transition ${
              viewMode === 'canopy' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            Canopy Only
          </button>
          <button
            id="view-roots-btn"
            onClick={() => setViewMode('roots')}
            className={`px-2.5 py-1 rounded transition ${
              viewMode === 'roots' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            Root Architecture
          </button>
          <button
            id="view-field-btn"
            onClick={() => setViewMode('field')}
            className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
              viewMode === 'field' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Grid3X3 className="w-3.5 h-3.5" />
            Field Grid (1000x)
          </button>
        </div>

        {/* Action Controls */}
        <div className="pointer-events-auto flex items-center gap-1.5 bg-slate-900/90 backdrop-blur p-1 rounded-lg border border-slate-700">
          <button
            id="toggle-stress-heatmap-btn"
            onClick={() => setShowStressHeatmap(!showStressHeatmap)}
            title="Toggle Water Stress Heatmap"
            className={`p-1.5 rounded transition text-xs flex items-center gap-1 ${
              showStressHeatmap ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Thermometer className="w-3.5 h-3.5" />
            Stress
          </button>
          <button
            id="toggle-xylem-flux-btn"
            onClick={() => setAnimateXylemFlux(!animateXylemFlux)}
            title="Toggle Xylem Sap Flux"
            className={`p-1.5 rounded transition text-xs flex items-center gap-1 ${
              animateXylemFlux ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Droplets className="w-3.5 h-3.5" />
            Flux
          </button>
          <button
            id="reset-cam-btn"
            onClick={resetCamera}
            title="Reset Camera View"
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            id="fullscreen-toggle-btn"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main 3D WebGL Canvas container */}
      <div ref={mountRef} className="w-full flex-1 cursor-grab active:cursor-grabbing relative" />

      {/* Floating Organ Telemetry Card */}
      <div className="absolute left-4 bottom-18 z-10 pointer-events-auto bg-slate-900/90 backdrop-blur-md p-3 rounded-lg border border-slate-700/80 shadow-xl max-w-xs text-xs space-y-2">
        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
          <span className="font-semibold text-slate-200 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            FSPM Dynamic Biophysics
          </span>
          <span className="text-[10px] text-slate-400">Day {day} (VE+{day})</span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-slate-300">
          <div className="bg-slate-800/60 p-1.5 rounded">
            <div className="text-[10px] text-slate-400">Plant Height</div>
            <div className="text-sm font-semibold text-white">{plantData.plantHeightCm} cm</div>
          </div>
          <div className="bg-slate-800/60 p-1.5 rounded">
            <div className="text-[10px] text-slate-400">Max Root Depth</div>
            <div className="text-sm font-semibold text-amber-400">-{plantData.maxRootDepthCm} cm</div>
          </div>
          <div className="bg-slate-800/60 p-1.5 rounded">
            <div className="text-[10px] text-slate-400">Leaf Area Index (LAI)</div>
            <div className="text-sm font-semibold text-emerald-400">{plantData.leafAreaIndex} m²/m²</div>
          </div>
          <div className="bg-slate-800/60 p-1.5 rounded">
            <div className="text-[10px] text-slate-400">Transpiration</div>
            <div className="text-sm font-semibold text-cyan-400">{plantData.transpirationRateMmDay} mm/d</div>
          </div>
        </div>

        <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800">
          <span>Xylem Water Potential:</span>
          <span
            className={`font-semibold ${
              plantData.xylemPotentialMpa > -0.8
                ? 'text-emerald-400'
                : plantData.xylemPotentialMpa > -1.3
                ? 'text-amber-400'
                : 'text-rose-400'
            }`}
          >
            {plantData.xylemPotentialMpa} MPa
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>Crown Root Count:</span>
          <span className="font-semibold text-slate-200">{plantData.rootArchitecture.crownRootCount} roots</span>
        </div>
      </div>

      {/* Growth Stage Phenology Slider at Bottom */}
      <div className="absolute bottom-0 left-0 right-0 z-10 p-3 bg-slate-950/95 border-t border-slate-800 flex items-center gap-4 text-xs">
        <span className="text-slate-400 font-medium whitespace-nowrap">Phenology Timeline:</span>
        <div className="flex-1 flex flex-col gap-1">
          <input
            id="fspm-day-slider"
            type="range"
            min="1"
            max="120"
            value={day}
            onChange={(e) => setDay(parseInt(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
          <div className="flex justify-between text-[10px] text-slate-400 px-0.5">
            <span>VE (Emergence)</span>
            <span>V4 (4-Leaf)</span>
            <span>V8 (Knee-high)</span>
            <span>V12</span>
            <span>VT (Tassel)</span>
            <span>R1 (Silking)</span>
            <span>R6 (Maturity)</span>
          </div>
        </div>
        <span className="px-2 py-1 bg-slate-800 font-mono text-indigo-300 rounded border border-slate-700 min-w-[55px] text-center">
          Day {day}
        </span>
      </div>
    </div>
  );
};
