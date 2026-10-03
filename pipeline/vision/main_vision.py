import json
import argparse
from typing import List, Dict, Tuple
from pipeline.vision.finger_mapper import FingerKeyMapper

def process_video_frames(hands_data: List[Dict], quad: Tuple) -> List[Dict]:
    """
    Process extracted hand coordinates and map them to piano key events.
    """
    mapper = FingerKeyMapper(quad)
    return mapper.map_fingers_to_keys(hands_data, quad)

def main():
    parser = argparse.ArgumentParser(description='Map piano fingers to 88 keys')
    parser.add_argument('--input', type=str, required=True, help='Path to hand landmarks JSON')
    parser.add_argument('--quad', type=str, required=True, help='JSON string of 4 corner points [[x,y],...]')
    parser.add_argument('--output', type=str, required=True, help='Path to output JSON')

    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        hands_data = json.load(f)

    quad = json.loads(args.quad)
    quad_tuples = [tuple(p) for p in quad]

    results = process_video_frames(hands_data, quad_tuples)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"解析完了: {len(results)} 件の運指イベントを保存しました。")

if __name__ == '__main__':
    main()
