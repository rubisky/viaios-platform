/**
 * ModelViewer3D — Three.js 3D visualization for AI model outputs (P3)
 * Renders: bounding boxes, keypoints, trajectories in 3D scene
 */
import React, { useEffect, useRef } from 'react';
import { Spin } from 'antd';
// @ts-ignore — Three.js loaded from CDN or optional install
import * as THREE from 'three';

interface Props { detections?: BBox[]; keypoints?: Keypoint[][]; width?: number; height?: number; }
interface BBox { x: number; y: number; w: number; h: number; class: string; confidence: number; }
interface Keypoint { x: number; y: number; name: string; confidence: number; }

const COLORS: Record<string, number> = { person: 0x4ecdc4, vehicle: 0xff6b6b, face: 0x45b7d1 };

const ModelViewer3D: React.FC<Props> = ({ detections = [], keypoints = [], width = 400, height = 300 }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.set(3, 3, 5);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    containerRef.current.appendChild(renderer.domElement);

    // Lighting
    scene.add(new THREE.AmbientLight(0x404060, 0.6));
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(5, 10, 5);
    scene.add(dir);

    // Grid
    const grid = new THREE.GridHelper(6, 20, 0x2a2a4a, 0x1a1a3e);
    scene.add(grid);

    // Render detections as colored boxes
    detections.forEach(d => {
      const color = COLORS[d.class] || 0xffffff;
      const geo = new THREE.BoxGeometry(d.w / 200, d.h / 200, 0.1);
      const mat = new THREE.MeshPhongMaterial({ color, opacity: 0.7, transparent: true });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set((d.x - 0.5) * 2, -(d.y - 0.5) * 2, 0);
      scene.add(mesh);
    });

    // Render keypoints as spheres
    keypoints.forEach((kps, i) => {
      kps.forEach(kp => {
        const geo = new THREE.SphereGeometry(0.03, 8, 8);
        const mat = new THREE.MeshPhongMaterial({ color: 0x00ff88 });
        const sphere = new THREE.Mesh(geo, mat);
        sphere.position.set((kp.x - 0.5) * 2, -(kp.y - 0.5) * 2, 0.2);
        scene.add(sphere);
      });
    });

    // Animate
    let frame = 0;
    const animate = () => {
      frame++;
      scene.rotation.y = Math.sin(frame * 0.005) * 0.3;
      renderer.render(scene, camera);
      const id = requestAnimationFrame(animate);
      return () => cancelAnimationFrame(id);
    };
    const cleanup = animate();

    return () => { cleanup(); renderer.dispose(); };
  }, [detections, keypoints, width, height]);

  return <div ref={containerRef} style={{ borderRadius: 8, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#1a1a2e' }}>
    {!detections.length && <span style={{ color: '#888', position: 'absolute' }}><Spin /> Loading 3D...</span>}
  </div>;
};

export default ModelViewer3D;
