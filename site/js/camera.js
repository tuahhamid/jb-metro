// Camera moves for tour and places. With reduced motion: jump, no fly, no orbit.
export const FLY_MS = 2600;

export function cameraMove(camera, { reduced = false } = {}) {
  const options = { center: camera.center, zoom: camera.zoom, bearing: camera.bearing, pitch: camera.pitch };
  if (reduced) return { method: "jumpTo", options };
  return { method: "flyTo", options: { ...options, duration: FLY_MS, essential: true } };
}
