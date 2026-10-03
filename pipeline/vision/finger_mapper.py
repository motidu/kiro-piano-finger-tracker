import math
from typing import List, Tuple, Dict

class FingerKeyMapper:
    """Maps finger positions to piano keys based on a quadrilateral bounding box (Zero-Dependency)."""

    FINGER_NAMES = {
        1: "Thumb",
        2: "Index",
        3: "Middle",
        4: "Ring",
        5: "Pinky"
    }

    def __init__(self, quad: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]):
        """
        Initialize the mapper with a quadrilateral (quad) representing the piano key region.
        quad: ((x1, y1), (x2, y2), (x3, y3), (x4, y4))
        Order: P1(top-left), P2(top-right), P3(bottom-right), P4(bottom-left)
        """
        self.quad = list(quad)

    def _solve_bilinear(self, x: float, y: float, u_guess: float = 0.5, v_guess: float = 0.5, iterations: int = 15, tolerance: float = 1e-6) -> Tuple[float, float]:
        """
        Solve for u, v in [0, 1] using Newton-Raphson such that the bilinear interpolation
        of quad corners yields (x, y).
        """
        p1, p2, p3, p4 = self.quad
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        u = float(u_guess)
        v = float(v_guess)

        for _ in range(iterations):
            xu = x1 * (1 - u) * (1 - v) + x2 * u * (1 - v) + x3 * u * v + x4 * (1 - u) * v
            yu = y1 * (1 - u) * (1 - v) + y2 * u * (1 - v) + y3 * u * v + y4 * (1 - u) * v

            dx_du = (x2 - x1) * (1 - v) + (x3 - x4) * v
            dx_dv = (x4 - x1) * (1 - u) + (x3 - x2) * u
            dy_du = (y2 - y1) * (1 - v) + (y3 - y4) * v
            dy_dv = (y4 - y1) * (1 - u) + (y3 - y2) * u

            det = dx_du * dy_dv - dx_dv * dy_du
            if abs(det) < 1e-10:
                break

            du = ((x - xu) * dy_dv - (y - yu) * dx_dv) / det
            dv = ((y - yu) * dx_du - (x - xu) * dy_du) / det

            u += du
            v += dv

            u = max(0.0, min(1.0, float(u)))
            v = max(0.0, min(1.0, float(v)))

            if abs(du) < tolerance and abs(dv) < tolerance:
                break

        return float(u), float(v)

    def map_fingers_to_keys(self, hands: List[Dict], quad: Tuple = None) -> List[Dict]:
        """
        Assign fingers to piano keys (88 keys: MIDI 21 to 108).
        """
        if quad is not None:
            self.quad = list(quad)

        results = []
        min_midi = 21
        max_midi = 108

        for hand_data in hands:
            hand_id = hand_data.get('hand_id', 0)
            fingers = hand_data.get('fingers', [])

            for finger in fingers:
                x = finger.get('x', 0.0)
                y = finger.get('y', 0.0)
                finger_id = finger.get('finger_id', 1)

                u, v = self._solve_bilinear(x, y)

                midi_note = int(round(min_midi + u * (max_midi - min_midi)))
                midi_note = max(min_midi, min(max_midi, midi_note))

                results.append({
                    'timestamp': hand_data.get('timestamp', 0.0),
                    'note': midi_note,
                    'finger': finger_id,
                    'hand': hand_id,
                    'u': round(u, 4),
                    'v': round(v, 4)
                })

        return results
