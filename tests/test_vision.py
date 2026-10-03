import pytest
from pipeline.vision.finger_mapper import FingerKeyMapper

def test_bilinear_interpolation():
    """正方形のクアッドに対してバイリニア補間が正確に逆変換されるか検証"""
    quad = ((0, 0), (100, 0), (100, 100), (0, 100))
    mapper = FingerKeyMapper(quad)

    # 中心点: u=0.5, v=0.5 -> (50, 50)
    u, v = mapper._solve_bilinear(50, 50)
    assert abs(u - 0.5) < 1e-2
    assert abs(v - 0.5) < 1e-2

    # 左上: u=0, v=0 -> (0, 0)
    u, v = mapper._solve_bilinear(0, 0)
    assert abs(u - 0.0) < 1e-2
    assert abs(v - 0.0) < 1e-2

    # 右下: u=1, v=1 -> (100, 100)
    u, v = mapper._solve_bilinear(100, 100)
    assert abs(u - 1.0) < 1e-2
    assert abs(v - 1.0) < 1e-2

def test_key_bounding_box_generation():
    """88鍵盤の端点（A0: MIDI 21、C8: MIDI 108）が正確に判定されるか検証"""
    quad = ((0, 0), (100, 0), (100, 100), (0, 100))
    mapper = FingerKeyMapper(quad)

    hands = [
        {
            'timestamp': 0.0,
            'hand_id': 0,
            'fingers': [
                {'x': 0, 'y': 50, 'finger_id': 1},   # 最左端 -> MIDI 21 (A0)
                {'x': 100, 'y': 50, 'finger_id': 2}, # 最右端 -> MIDI 108 (C8)
            ]
        }
    ]

    results = mapper.map_fingers_to_keys(hands, quad)
    assert results[0]['note'] == 21
    assert results[1]['note'] == 108

def test_fingertip_mapping():
    """5本の指番号（1:親指 〜 5:小指）と左右の手情報が保持されるか検証"""
    quad = ((0, 0), (100, 0), (100, 100), (0, 100))
    mapper = FingerKeyMapper(quad)

    hands = [
        {
            'timestamp': 1.0,
            'hand_id': 1,
            'fingers': [
                {'x': 50, 'y': 50, 'finger_id': 1},
                {'x': 25, 'y': 50, 'finger_id': 2},
                {'x': 75, 'y': 50, 'finger_id': 3},
                {'x': 10, 'y': 50, 'finger_id': 4},
                {'x': 90, 'y': 50, 'finger_id': 5},
            ]
        }
    ]

    results = mapper.map_fingers_to_keys(hands, quad)
    assert results[0]['finger'] == 1
    assert results[1]['finger'] == 2
    assert results[2]['finger'] == 3
    assert results[3]['finger'] == 4
    assert results[4]['finger'] == 5
    assert all(r['hand'] == 1 for r in results)
