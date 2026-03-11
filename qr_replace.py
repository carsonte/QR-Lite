from __future__ import annotations

import os
import tempfile
import io
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageCms


@dataclass
class ReplaceResult:
    output_path: str
    qr_count: int
    original_mode: str
    original_format: str
    output_format: str
    image_width: int
    image_height: int
    selected_quad: list[list[float]] | None
    replacement_qr_box: list[float] | None
    target_box: list[float] | None


def _order_quad(points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _quad_area(points: np.ndarray) -> float:
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    return float(abs(cv2.contourArea(pts)))


def _extract_quads(points: np.ndarray | None) -> list[np.ndarray]:
    if points is None:
        return []

    arr = np.asarray(points, dtype=np.float32)
    quads: list[np.ndarray] = []
    if arr.ndim == 2 and arr.shape == (4, 2):
        quads.append(_order_quad(arr))
    elif arr.ndim == 3 and arr.shape[1:] == (4, 2):
        for item in arr:
            quads.append(_order_quad(item))
    elif arr.ndim == 3 and arr.shape[0:2] == (1, 4):
        quads.append(_order_quad(arr[0]))
    return quads


def _detect_qr_quads(image_bgr: np.ndarray) -> list[np.ndarray]:
    detector = cv2.QRCodeDetector()
    quads: list[np.ndarray] = []

    try:
        multi_result = detector.detectAndDecodeMulti(image_bgr)
        if isinstance(multi_result, tuple):
            if len(multi_result) == 4:
                ok, _decoded, points, _ = multi_result
                if ok:
                    quads.extend(_extract_quads(points))
            elif len(multi_result) == 3:
                _decoded, points, _ = multi_result
                quads.extend(_extract_quads(points))
    except Exception:
        pass

    if quads:
        return quads

    try:
        single_result = detector.detectAndDecode(image_bgr)
        if isinstance(single_result, tuple):
            if len(single_result) == 3:
                _decoded, points, _ = single_result
                quads.extend(_extract_quads(points))
            elif len(single_result) == 2:
                _decoded, points = single_result
                quads.extend(_extract_quads(points))
    except Exception:
        pass

    if quads:
        return quads

    try:
        detect_result = detector.detect(image_bgr)
        if isinstance(detect_result, tuple) and len(detect_result) >= 2:
            ok, points = detect_result[0], detect_result[1]
            if ok:
                quads.extend(_extract_quads(points))
    except Exception:
        pass

    return quads


def _detect_qr_quads_downscaled(image_bgr: np.ndarray, max_side: int = 1600) -> list[np.ndarray]:
    h, w = image_bgr.shape[:2]
    longest_side = max(h, w)
    if longest_side <= max_side:
        return _detect_qr_quads(image_bgr)

    scale = max_side / float(longest_side)
    resized_w = max(1, int(round(w * scale)))
    resized_h = max(1, int(round(h * scale)))
    resized = cv2.resize(image_bgr, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
    quads = _detect_qr_quads(resized)
    if not quads:
        return _detect_qr_quads(image_bgr)

    scale_back = np.array(
        [w / float(resized_w), h / float(resized_h)],
        dtype=np.float32,
    )
    return [quad * scale_back for quad in quads]


def _detect_qr_quads_with_fallback_crops(image_bgr: np.ndarray) -> list[np.ndarray]:
    h, w = image_bgr.shape[:2]
    candidates: list[tuple[np.ndarray, int, int]] = [(image_bgr, 0, 0)]

    for ratio in (0.95, 0.9, 0.85, 0.8, 0.75, 0.7):
        crop_h = max(1, int(h * ratio))
        candidates.append((image_bgr[:crop_h, :], 0, 0))

    square_side = min(h, w)
    if square_side > 0 and square_side != w:
        x0 = max(0, (w - square_side) // 2)
        candidates.append((image_bgr[:, x0 : x0 + square_side], x0, 0))

    for crop, offset_x, offset_y in candidates:
        quads = _detect_qr_quads(crop)
        if quads:
            if offset_x or offset_y:
                offset = np.array([offset_x, offset_y], dtype=np.float32)
                return [quad + offset for quad in quads]
            return quads
    return []


def _estimate_qr_bbox_from_components(qr_rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(qr_rgb, cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

    h, w = mask.shape[:2]
    kernel_size = max(5, int(min(h, w) * 0.035))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    merged = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    merged = cv2.dilate(merged, kernel, iterations=1)

    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_box: tuple[int, int, int, int] | None = None
    best_score = 0.0

    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = bw * bh
        if area < (h * w * 0.04):
            continue
        aspect = min(bw, bh) / max(bw, bh)
        vertical_center = y + (bh / 2.0)
        top_bias = 1.0 if vertical_center < h * 0.8 else 0.6
        score = area * (aspect**2) * top_bias
        if score > best_score:
            best_score = score
            best_box = (x, y, bw, bh)

    if best_box is None:
        return None

    x, y, bw, bh = best_box
    side = int(max(bw, bh))
    pad = max(4, int(side * 0.03))
    side += pad * 2

    cx = x + (bw / 2.0)
    cy = y + (bh / 2.0)
    x0 = int(round(cx - side / 2.0))
    y0 = int(round(cy - side / 2.0))
    x1 = x0 + side
    y1 = y0 + side

    if x0 < 0:
        x1 -= x0
        x0 = 0
    if y0 < 0:
        y1 -= y0
        y0 = 0
    if x1 > w:
        shift = x1 - w
        x0 = max(0, x0 - shift)
        x1 = w
    if y1 > h:
        shift = y1 - h
        y0 = max(0, y0 - shift)
        y1 = h

    return x0, y0, x1, y1


def _extract_qr_region(qr_rgb: np.ndarray) -> np.ndarray:
    qr_bgr = cv2.cvtColor(qr_rgb, cv2.COLOR_RGB2BGR)
    quads = _detect_qr_quads_with_fallback_crops(qr_bgr)
    if not quads:
        bbox = _estimate_qr_bbox_from_components(qr_rgb)
        if bbox is not None:
            x0, y0, x1, y1 = bbox
            return qr_rgb[y0:y1, x0:x1]
        return qr_rgb

    quad = max(quads, key=_quad_area)
    quad = _order_quad(quad)
    top = np.linalg.norm(quad[1] - quad[0])
    right = np.linalg.norm(quad[2] - quad[1])
    bottom = np.linalg.norm(quad[2] - quad[3])
    left = np.linalg.norm(quad[3] - quad[0])
    side = max(1, int(max(top, right, bottom, left)))

    src_pts = quad.astype(np.float32)
    dst_pts = np.array(
        [[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped_bgr = cv2.warpPerspective(
        qr_bgr,
        matrix,
        (side, side),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2RGB)


def _detect_qr_crop_box(qr_rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    qr_bgr = cv2.cvtColor(qr_rgb, cv2.COLOR_RGB2BGR)
    quads = _detect_qr_quads_with_fallback_crops(qr_bgr)
    if quads:
        quad = _order_quad(max(quads, key=_quad_area))
        xs = quad[:, 0]
        ys = quad[:, 1]
        side = max(float(xs.max() - xs.min()), float(ys.max() - ys.min()))
        pad = max(2, int(side * 0.03))
        h, w = qr_rgb.shape[:2]
        x0 = max(0, int(np.floor(xs.min())) - pad)
        y0 = max(0, int(np.floor(ys.min())) - pad)
        x1 = min(w, int(np.ceil(xs.max())) + pad)
        y1 = min(h, int(np.ceil(ys.max())) + pad)
        if x1 > x0 and y1 > y0:
            return x0, y0, x1, y1
    return _estimate_qr_bbox_from_components(qr_rgb)


def _sanitize_crop_box(
    crop_box: tuple[float, float, float, float] | None,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    if crop_box is None:
        return None
    x, y, w, h = crop_box
    if w <= 1 or h <= 1:
        return None

    x0 = int(round(x))
    y0 = int(round(y))
    x1 = int(round(x + w))
    y1 = int(round(y + h))

    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    return x0, y0, x1, y1


def _box_to_xywh(box: tuple[int, int, int, int] | None) -> list[float] | None:
    if box is None:
        return None
    x0, y0, x1, y1 = box
    return [float(x0), float(y0), float(x1 - x0), float(y1 - y0)]


def _box_to_quad(box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    return np.array(
        [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        dtype=np.float32,
    )


def _crop_qr_content(qr_rgb: np.ndarray, white_threshold: int = 245) -> np.ndarray:
    if qr_rgb.size == 0:
        return qr_rgb

    non_white_mask = np.any(qr_rgb < white_threshold, axis=2)
    ys, xs = np.where(non_white_mask)
    if len(xs) == 0 or len(ys) == 0:
        return qr_rgb

    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    return qr_rgb[y0:y1, x0:x1]


def _prepare_qr_square(qr_rgb: np.ndarray, size: int, quiet_zone_ratio: float = 0.025) -> np.ndarray:
    canvas = np.full((size, size, 3), 255, dtype=np.uint8)
    cropped = _crop_qr_content(_extract_qr_region(qr_rgb))
    h, w = cropped.shape[:2]
    if h < 1 or w < 1:
        return canvas

    margin = max(0, int(size * quiet_zone_ratio))
    inner = max(1, size - 2 * margin)
    scale = min(inner / float(w), inner / float(h))
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    y = (size - new_h) // 2
    x = (size - new_w) // 2
    canvas[y : y + new_h, x : x + new_w] = resized
    return canvas


def _recommended_blend_side(quad: np.ndarray) -> int:
    dst_pts = _order_quad(quad)
    edge_lengths = [
        np.linalg.norm(dst_pts[1] - dst_pts[0]),
        np.linalg.norm(dst_pts[2] - dst_pts[1]),
        np.linalg.norm(dst_pts[2] - dst_pts[3]),
        np.linalg.norm(dst_pts[3] - dst_pts[0]),
    ]
    target_side = float(max(edge_lengths))
    return int(max(64, min(1800, round(target_side * 1.35))))


def _blend_square_to_quad(
    base_img: np.ndarray,
    square_img: np.ndarray,
    quad: np.ndarray,
    feather_ratio: float,
    border_value: int | tuple[int, ...],
) -> np.ndarray:
    h, w = base_img.shape[:2]
    dst_pts = _order_quad(quad)
    edge_lengths = [
        np.linalg.norm(dst_pts[1] - dst_pts[0]),
        np.linalg.norm(dst_pts[2] - dst_pts[1]),
        np.linalg.norm(dst_pts[2] - dst_pts[3]),
        np.linalg.norm(dst_pts[3] - dst_pts[0]),
    ]
    side = square_img.shape[0]
    src_pts = np.array(
        [[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
        dtype=np.float32,
    )

    xs = dst_pts[:, 0]
    ys = dst_pts[:, 1]
    k = int(max(1, min(max(edge_lengths), max(1.0, min(h, w))) * feather_ratio))
    if k % 2 == 0:
        k += 1

    pad = max(2, k * 2)
    x0 = max(0, int(np.floor(xs.min())) - pad)
    y0 = max(0, int(np.floor(ys.min())) - pad)
    x1 = min(w, int(np.ceil(xs.max())) + pad)
    y1 = min(h, int(np.ceil(ys.max())) + pad)
    if x1 <= x0 or y1 <= y0:
        return base_bgr

    local_dst_pts = dst_pts - np.array([x0, y0], dtype=np.float32)
    roi_w = x1 - x0
    roi_h = y1 - y0
    matrix = cv2.getPerspectiveTransform(src_pts, local_dst_pts)
    warped = cv2.warpPerspective(
        square_img,
        matrix,
        (roi_w, roi_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )

    mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
    cv2.fillConvexPoly(mask, local_dst_pts.astype(np.int32), 255)
    mask_f = cv2.GaussianBlur(mask, (k, k), 0).astype(np.float32) / 255.0
    alpha = np.clip(mask_f[..., None], 0.0, 1.0)

    base_roi = base_img[y0:y1, x0:x1].astype(np.float32)
    out_roi = warped.astype(np.float32) * alpha + base_roi * (1.0 - alpha)
    out = base_img.copy()
    out[y0:y1, x0:x1] = out_roi.astype(np.uint8)
    return out


def _blend_quad(
    base_bgr: np.ndarray,
    qr_bgr: np.ndarray,
    quad: np.ndarray,
    feather_ratio: float,
    quiet_zone_ratio: float,
) -> np.ndarray:
    side = _recommended_blend_side(quad)
    qr_square = _prepare_qr_square(
        cv2.cvtColor(qr_bgr, cv2.COLOR_BGR2RGB),
        side,
        quiet_zone_ratio=quiet_zone_ratio,
    )
    qr_square_bgr = cv2.cvtColor(qr_square, cv2.COLOR_RGB2BGR)
    return _blend_square_to_quad(
        base_img=base_bgr,
        square_img=qr_square_bgr,
        quad=quad,
        feather_ratio=feather_ratio,
        border_value=(255, 255, 255),
    )


def _rgb_to_cmyk_array(rgb_array: np.ndarray, target_icc_profile: bytes | None = None) -> np.ndarray:
    rgb_image = Image.fromarray(rgb_array, mode="RGB")
    if target_icc_profile:
        try:
            srgb_profile = ImageCms.createProfile("sRGB")
            cmyk_profile = ImageCms.getOpenProfile(io.BytesIO(target_icc_profile))
            converted = ImageCms.profileToProfile(
                rgb_image,
                srgb_profile,
                cmyk_profile,
                outputMode="CMYK",
            )
            return np.array(converted)
        except Exception:
            pass
    return np.array(rgb_image.convert("CMYK"))


def _choose_quads(quads: list[np.ndarray], replace_all: bool) -> list[np.ndarray]:
    if replace_all:
        return sorted(quads, key=_quad_area, reverse=True)
    return [max(quads, key=_quad_area)]


def _transform_quad(
    quad: np.ndarray,
    offset_x_px: float,
    offset_y_px: float,
    scale_ratio: float,
    rotation_deg: float,
) -> np.ndarray:
    pts = np.asarray(quad, dtype=np.float32).reshape(4, 2)
    center = pts.mean(axis=0, keepdims=True)
    local = pts - center
    local = local * float(scale_ratio)

    if abs(rotation_deg) > 1e-8:
        rad = np.deg2rad(rotation_deg)
        cos_v = float(np.cos(rad))
        sin_v = float(np.sin(rad))
        rot = np.array([[cos_v, -sin_v], [sin_v, cos_v]], dtype=np.float32)
        local = local @ rot.T

    shift = np.array([[float(offset_x_px), float(offset_y_px)]], dtype=np.float32)
    return (local + center + shift).astype(np.float32)


def _normalize_output_format(src_format: str, output_format: str) -> str:
    fmt = output_format.strip().upper()
    if fmt == "SAME":
        return "JPEG" if src_format in ("JPG", "JPEG") else "PNG"
    if fmt in ("JPG", "JPEG"):
        return "JPEG"
    if fmt == "PNG":
        return "PNG"
    raise ValueError("output_format only supports SAME / PNG / JPEG")


def replace_qr(
    source_image_path: str,
    replacement_qr_path: str,
    output_path: Optional[str] = None,
    placement_mode: str = "auto",
    replace_all: bool = False,
    feather_ratio: float = 0.012,
    output_format: str = "SAME",
    offset_x_px: float = 0.0,
    offset_y_px: float = 0.0,
    scale_ratio: float = 1.0,
    rotation_deg: float = 0.0,
    quiet_zone_ratio: float = 0.025,
    replacement_crop_box: tuple[float, float, float, float] | None = None,
    target_box: tuple[float, float, float, float] | None = None,
) -> ReplaceResult:
    if scale_ratio <= 0.0:
        raise ValueError("scale_ratio must be greater than 0.")
    if quiet_zone_ratio < 0.0 or quiet_zone_ratio > 0.2:
        raise ValueError("quiet_zone_ratio must be between 0 and 0.2.")

    mode = (placement_mode or "auto").strip().lower()
    if mode not in ("auto", "manual"):
        raise ValueError("placement_mode only supports auto / manual")

    src_img = Image.open(source_image_path)
    src_mode = src_img.mode
    src_format = (src_img.format or os.path.splitext(source_image_path)[1].lstrip(".") or "PNG").upper()
    src_info = dict(src_img.info)
    src_exif = src_img.getexif()
    output_fmt = _normalize_output_format(src_format, output_format)
    preserve_cmyk_output = src_mode == "CMYK" and output_fmt == "JPEG"

    src_rgb = src_img.convert("RGB")
    src_np_rgb = np.array(src_rgb)
    src_bgr = cv2.cvtColor(src_np_rgb, cv2.COLOR_RGB2BGR)

    manual_target_box = _sanitize_crop_box(target_box, src_bgr.shape[1], src_bgr.shape[0])
    if mode == "manual":
        if manual_target_box is None:
            raise ValueError("手动模式需要先在右边图片上框出要放二维码的位置。")
        quads = [_box_to_quad(manual_target_box)]
    else:
        quads = _detect_qr_quads_downscaled(src_bgr)
        if not quads:
            raise ValueError("没找到原二维码。如果这张图里本来就没有二维码，请改用“图里没有原二维码，我手动放一个”。")

    selected_quads = _choose_quads(quads, replace_all=replace_all and mode == "auto")

    qr_img = Image.open(replacement_qr_path).convert("RGB")
    qr_rgb = np.array(qr_img)
    manual_qr_box = _sanitize_crop_box(replacement_crop_box, qr_rgb.shape[1], qr_rgb.shape[0])
    effective_qr_box = manual_qr_box or _detect_qr_crop_box(qr_rgb)
    if effective_qr_box is not None:
        x0, y0, x1, y1 = effective_qr_box
        qr_rgb = qr_rgb[y0:y1, x0:x1]
    qr_bgr = cv2.cvtColor(qr_rgb, cv2.COLOR_RGB2BGR)

    out_bgr = src_bgr.copy()
    out_cmyk = np.array(src_img.convert("CMYK")) if preserve_cmyk_output else None
    first_transformed_quad: np.ndarray | None = None
    for quad in selected_quads:
        transformed_quad = _transform_quad(
            quad=quad,
            offset_x_px=offset_x_px,
            offset_y_px=offset_y_px,
            scale_ratio=scale_ratio,
            rotation_deg=rotation_deg,
        )
        if first_transformed_quad is None:
            first_transformed_quad = transformed_quad.copy()
        if preserve_cmyk_output and out_cmyk is not None:
            qr_square_rgb = _prepare_qr_square(
                qr_rgb,
                _recommended_blend_side(transformed_quad),
                quiet_zone_ratio=quiet_zone_ratio,
            )
            qr_square_cmyk = _rgb_to_cmyk_array(qr_square_rgb, src_info.get("icc_profile"))
            out_cmyk = _blend_square_to_quad(
                base_img=out_cmyk,
                square_img=qr_square_cmyk,
                quad=transformed_quad,
                feather_ratio=feather_ratio,
                border_value=(0, 0, 0, 0),
            )
        else:
            out_bgr = _blend_quad(
                out_bgr,
                qr_bgr,
                transformed_quad,
                feather_ratio=feather_ratio,
                quiet_zone_ratio=quiet_zone_ratio,
            )

    if preserve_cmyk_output and out_cmyk is not None:
        out_img = Image.fromarray(out_cmyk, mode="CMYK")
    else:
        out_rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
        out_img = Image.fromarray(out_rgb)

    if src_mode == "CMYK" and output_fmt == "JPEG" and out_img.mode != "CMYK":
        out_img = out_img.convert("CMYK")
    elif src_mode in ("RGBA", "LA") and output_fmt == "PNG":
        out_img = out_img.convert("RGBA")
        if "A" in src_img.getbands():
            out_img.putalpha(src_img.getchannel("A"))
    elif output_fmt == "JPEG" and out_img.mode in ("RGBA", "LA"):
        out_img = out_img.convert("RGB")

    if output_path is None:
        suffix = ".jpg" if output_fmt == "JPEG" else ".png"
        fd, output_path = tempfile.mkstemp(prefix="qr_replaced_", suffix=suffix)
        os.close(fd)

    save_kwargs = {}
    if "icc_profile" in src_info:
        save_kwargs["icc_profile"] = src_info["icc_profile"]
    if "dpi" in src_info:
        save_kwargs["dpi"] = src_info["dpi"]
    if src_exif:
        save_kwargs["exif"] = src_exif.tobytes()

    if output_fmt == "JPEG":
        save_kwargs.setdefault("quality", 95)
        save_kwargs.setdefault("subsampling", 0)
        out_img.save(output_path, format="JPEG", **save_kwargs)
    else:
        out_img.save(output_path, format="PNG", **save_kwargs)

    return ReplaceResult(
        output_path=output_path,
        qr_count=len(quads) if mode == "auto" else 0,
        original_mode=src_mode,
        original_format=src_format,
        output_format=output_fmt,
        image_width=int(src_bgr.shape[1]),
        image_height=int(src_bgr.shape[0]),
        selected_quad=first_transformed_quad.tolist() if first_transformed_quad is not None else None,
        replacement_qr_box=_box_to_xywh(effective_qr_box),
        target_box=_box_to_xywh(manual_target_box),
    )
