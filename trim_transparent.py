#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
透明边裁剪脚本 · 三文鱼之神
- 遍历 img/ 下所有 PNG，按非透明像素计算包围框，裁掉透明边
- 裁剪结果保存到 img_trimmed/，保持文件名一致
- 同时生成 trim_metadata.json，记录每张图在「原图 2000×2000」里的 (x,y,w,h)
  游戏里用裁剪图时，用这个偏移对齐，筷子+食物叠在一起的位置就不会错
"""

from pathlib import Path
import json

try:
    from PIL import Image
    import numpy as np
except ImportError as e:
    print("请先安装: pip install Pillow numpy")
    raise

# 与游戏里 trimCanvas 一致：alpha 大于此值视为不透明
ALPHA_THRESHOLD = 10

IMG_DIR = Path(__file__).resolve().parent / "img"
OUT_DIR = Path(__file__).resolve().parent / "img_trimmed"
META_PATH = Path(__file__).resolve().parent / "trim_metadata.json"


def get_content_bbox(im):
    """根据 alpha 通道得到非透明区域的 (left, top, right, bottom)，与游戏里 alpha > 10 一致。"""
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    a = np.array(im)[:, :, 3]
    rows = np.any(a > ALPHA_THRESHOLD, axis=1)
    cols = np.any(a > ALPHA_THRESHOLD, axis=0)
    if not np.any(rows) or not np.any(cols):
        return None
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return (int(cmin), int(rmin), int(cmax) + 1, int(rmax) + 1)


def trim_one(path: Path):
    """裁剪一张图，返回 (裁剪后的 PIL Image, 元数据 dict)。"""
    im = Image.open(path).convert("RGBA")
    w0, h0 = im.size
    bbox = get_content_bbox(im)
    if not bbox:
        # 全透明，不裁，直接保存原图并记录整图为框
        return im, {"x": 0, "y": 0, "w": w0, "h": h0, "origW": w0, "origH": h0}

    left, top, right, bottom = bbox
    # 可选：用 alpha 阈值再扫一遍，与游戏逻辑完全一致（getbbox 用的是任意非零）
    # 这里用 getbbox 通常就够用；若需与前端一致可改成逐像素 alpha > ALPHA_THRESHOLD
    cropped = im.crop((left, top, right, bottom))
    meta = {
        "x": left,
        "y": top,
        "w": right - left,
        "h": bottom - top,
        "origW": w0,
        "origH": h0,
    }
    return cropped, meta


def main():
    if not IMG_DIR.is_dir():
        print(f"找不到目录: {IMG_DIR}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {}

    for path in sorted(IMG_DIR.glob("*.PNG")) + sorted(IMG_DIR.glob("*.png")):
        name = path.name
        try:
            cropped, meta = trim_one(path)
            out_path = OUT_DIR / name
            cropped.save(out_path, "PNG")
            metadata[name] = meta
            print(f"OK {name} -> {meta['w']}x{meta['h']} @ ({meta['x']},{meta['y']})")
        except Exception as e:
            print(f"SKIP {name}: {e}")
            metadata[name] = None

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 同时生成 .js，供页面直接引用，无需 fetch，支持 file:// 打开
    js_path = META_PATH.parent / "trim_metadata.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.TRIM_METADATA = " + json.dumps(metadata) + ";")

    print(f"\n裁剪结果: {OUT_DIR}")
    print(f"元数据:   {META_PATH} 与 {js_path}")
    print("游戏里用 img_trimmed/ 的图时，用 trim_metadata 做偏移即可保持筷子与食物对齐。直接打开 index.html 即可运行，无需服务器。")


if __name__ == "__main__":
    main()
