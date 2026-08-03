from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
ZH_FONTS = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
)
EN_FONTS = (Path(r"C:\Windows\Fonts\arial.ttf"), Path("DejaVuSans.ttf"))
EN_BOLD_FONTS = (Path(r"C:\Windows\Fonts\arialbd.ttf"), Path("DejaVuSans-Bold.ttf"))

# Exact-run maps are 4× nearest-neighbour previews of the 342×275 model grid.
# Pixel centres therefore follow x=4*col+2, y=4*row+2.
SOURCE_XY = (258, 422)  # row=105, col=64 from the source lon/lat transform
OUTLET_XY = (338, 414)  # row=103, col=84 from conservative-model.npz
CRISM_XY = {
    "C1": (670, 598),  # row=149, col=167
    "P1": (674, 618),  # row=154, col=168
    "A1": (622, 570),  # row=142, col=155
}
PULSES = ((0.00, 0.02, 1.00), (0.02, 0.08, 0.35), (0.25, 0.28, 0.80), (0.55, 0.57, 0.60))

COLORS = {
    "ink": "#18262c",
    "muted": "#5c6b71",
    "grid": "#d9dfe1",
    "low": "#4a91c7",
    "medium": "#dc8c45",
    "high": "#8a5faf",
    "source": "#ff7b3b",
    "outlet": "#1ab88b",
    "crism": "#42b85f",
    "loss": "#c7c7c7",
    "basin": "#54a6d8",
    "surface": "#234f91",
    "boundary": "#1d2c49",
}


def font(size: int, *, bold: bool = False, zh: bool = True) -> ImageFont.FreeTypeFont:
    candidates = ZH_FONTS if zh else (EN_BOLD_FONTS if bold else EN_FONTS)
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.truetype("DejaVuSans.ttf", size)


def completed_outputs(project: Path) -> Path:
    for candidate in (project / "data" / "completed-runs", project / "outputs"):
        if (candidate / "low_summary.json").exists() and (candidate / "high_summary.json").exists():
            return candidate
    raise FileNotFoundError("completed low/high outputs were not found")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rounded(draw: ImageDraw.ImageDraw, box, radius=18, fill="#ffffff", outline="#cbd3d6", width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_box(draw, text, xy, max_width, fnt, fill, spacing=8):
    x, y = xy
    words = list(text) if any("\u4e00" <= c <= "\u9fff" for c in text) else text.split(" ")
    lines, line = [], ""
    glue = "" if words and len(words[0]) == 1 else " "
    for token in words:
        trial = token if not line else line + glue + token
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = token
    if line:
        lines.append(line)
    line_h = draw.textbbox((0, 0), "Hg国", font=fnt)[3] + spacing
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def annotate_map(base: Image.Image, zh: bool) -> Image.Image:
    image = base.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    f_label = font(25, bold=True, zh=zh)
    labels = {
        "source": "等效出水点" if zh else "Equivalent source",
        "outlet": "天然溢流口" if zh else "Natural spillway",
    }

    def marker(point, color, radius=10):
        x, y = point
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline="#071014", width=4)

    def label(point, text, color, dx=16, dy=-34, align="right"):
        x, y = point
        box = draw.textbbox((0, 0), text, font=f_label)
        w, h = box[2] - box[0] + 16, box[3] - box[1] + 12
        bx = x + dx if align == "right" else x - dx - w
        by = y + dy
        anchor_x = bx if align == "right" else bx + w
        draw.line((x, y, anchor_x, by + h // 2), fill=color, width=3)
        draw.rounded_rectangle((bx, by, bx + w, by + h), 5, fill="#0b1416ec")
        draw.text((bx + 8, by + 4), text, font=f_label, fill=color)

    marker(SOURCE_XY, COLORS["source"], 11)
    label(SOURCE_XY, labels["source"], "#ffd4be", 18, -64, "left")
    marker(OUTLET_XY, COLORS["outlet"], 10)
    label(OUTLET_XY, labels["outlet"], "#baffea", 18, 24, "right")
    crism_labels = {
        "C1": (22, -64, "right"),
        "P1": (24, 24, "right"),
        "A1": (18, -58, "left"),
    }
    for site, point in CRISM_XY.items():
        marker(point, COLORS["crism"], 10)
        dx, dy, align = crism_labels[site]
        label(point, site, "#c9ffd5", dx, dy, align)

    draw.line((48, image.height - 52, 248, image.height - 52), fill="white", width=7)
    draw.text((48, image.height - 100), "20 km", font=font(25, bold=True, zh=False), fill="white")
    draw.text((image.width - 64, 34), "N", font=font(34, bold=True, zh=False), fill="white")
    draw.line((image.width - 46, 82, image.width - 46, 132), fill="white", width=5)
    draw.polygon(
        ((image.width - 46, 68), (image.width - 58, 96), (image.width - 34, 96)),
        fill="white",
    )
    return image


def q_curve(key: str, t: np.ndarray) -> np.ndarray:
    if key == "low":
        return np.where(t <= 10.0, 100.0, np.nan)
    if key == "medium":
        return np.where(t <= 20.0, 300.0 + 3000.0 * np.exp(-t / 3.0), np.nan)
    q = np.full_like(t, 500.0)
    for a, b, mult in PULSES:
        mask = (t / 30.0 >= a) & (t / 30.0 < b)
        q[mask] += 5000.0 * mult
    return np.where(t <= 30.0, q, np.nan)


def draw_axes(draw, box, zh: bool):
    x0, y0, x1, y1 = box
    draw.line((x0, y1, x1, y1), fill=COLORS["ink"], width=3)
    draw.line((x0, y0, x0, y1), fill=COLORS["ink"], width=3)
    tick_font = font(24, zh=zh)
    for year in range(0, 31, 5):
        x = x0 + (x1 - x0) * year / 30
        draw.line((x, y1, x, y1 + 9), fill=COLORS["ink"], width=2)
        draw.text((x - 10, y1 + 14), str(year), font=tick_font, fill=COLORS["muted"])
        if year and year < 30:
            draw.line((x, y0, x, y1), fill=COLORS["grid"], width=1)
    for q in range(0, 6001, 1000):
        y = y1 - (y1 - y0) * q / 6000
        draw.line((x0 - 9, y, x0, y), fill=COLORS["ink"], width=2)
        draw.text((x0 - 82, y - 13), str(q), font=tick_font, fill=COLORS["muted"])
        if q:
            draw.line((x0, y, x1, y), fill=COLORS["grid"], width=1)
    draw.text(((x0 + x1) // 2 - 44, y1 + 60), "时间（年）" if zh else "Time (yr)", font=font(28, zh=zh), fill=COLORS["ink"])
    draw.text((x0 - 96, y0 - 46), "Q(t) (m³/s)", font=font(28, zh=False), fill=COLORS["ink"])


def draw_curve_panel(draw, box, zh: bool):
    x0, y0, x1, y1 = box
    rounded(draw, box, 22, "#ffffff", "#cbd3d6", 3)
    title = "（c）长期出流过程线" if zh else "(c) Long-term outflow hydrographs"
    draw.text((x0 + 32, y0 + 26), title, font=font(34, bold=True, zh=zh), fill=COLORS["ink"])
    plot = (x0 + 120, y0 + 118, x1 - 38, y1 - 92)
    draw_axes(draw, plot, zh)
    t = np.linspace(0, 30, 1801)
    for key, color in (("low", COLORS["low"]), ("medium", COLORS["medium"]), ("high", COLORS["high"])):
        q = q_curve(key, t)
        pts = []
        for ti, qi in zip(t, q):
            if np.isnan(qi):
                continue
            x = plot[0] + (plot[2] - plot[0]) * ti / 30.0
            y = plot[3] - (plot[3] - plot[1]) * qi / 6000.0
            pts.append((x, y))
        if len(pts) > 1:
            draw.line(pts, fill=color, width=6, joint="curve")
    legend = (
        ("低：恒定 100，T=10，C=0.4", "Low: constant 100, T=10, C=0.4"),
        ("中：300+3000 exp(-t/3)，T=20，C=0.7", "Medium: 300+3000 exp(-t/3), T=20, C=0.7"),
        ("高：500+分阶段脉冲，T=30，C=1.0", "High: 500 + staged pulses, T=30, C=1.0"),
    )
    for idx, (key, color) in enumerate((("low", COLORS["low"]), ("medium", COLORS["medium"]), ("high", COLORS["high"]))):
        lx = x0 + 160 + idx * 750
        ly = y0 + 77
        draw.line((lx, ly, lx + 54, ly), fill=color, width=7)
        draw.text((lx + 65, ly - 16), legend[idx][0 if zh else 1], font=font(24, zh=zh), fill=COLORS["muted"])


def draw_budget_panel(draw, box, low: dict, high: dict, zh: bool):
    x0, y0, x1, y1 = box
    rounded(draw, box, 22, "#ffffff", "#cbd3d6", 3)
    title = "（d）完成运行的水量收支" if zh else "(d) Water budgets of completed runs"
    draw.text((x0 + 32, y0 + 26), title, font=font(34, bold=True, zh=zh), fill=COLORS["ink"])
    labels = {
        "loss": "沿程损失" if zh else "Loss",
        "basin": "源洼地" if zh else "Source basin",
        "surface": "域内水体" if zh else "Surface storage",
        "boundary": "边界外排" if zh else "Boundary outflow",
    }
    categories = (
        ("loss", "loss_one_minus_c", COLORS["loss"]),
        ("basin", "source_basin_storage", COLORS["basin"]),
        ("surface", "downstream_surface_storage", COLORS["surface"]),
        ("boundary", "open_boundary_outflow", COLORS["boundary"]),
    )
    ledger_low = low["water_ledger_km3"]
    ledger_high = high["water_ledger_km3"]
    y = y0 + 118
    budget_names = (("低 / Low", ledger_low), ("高 / High", ledger_high)) if zh else (("Low", ledger_low), ("High", ledger_high))
    for name, ledger in budget_names:
        raw = ledger["raw_release"]
        draw.text((x0 + 42, y + 22), name, font=font(28, bold=True, zh=zh), fill=COLORS["ink"])
        bx0, bx1 = x0 + 220, x1 - 42
        cur = bx0
        for _, field, color in categories:
            value = max(0.0, ledger[field])
            width = (bx1 - bx0) * value / raw if raw else 0
            draw.rectangle((cur, y, cur + width, y + 68), fill=color)
            cur += width
        draw.rounded_rectangle((bx0, y, bx1, y + 68), 6, outline="#839095", width=2)
        draw.text((bx0, y + 82), f"{raw:,.3f} km³", font=font(26, bold=True, zh=False), fill=COLORS["ink"])
        y += 190
    lx, ly = x0 + 42, y0 + 510
    for idx, (key, _, color) in enumerate(categories):
        col = idx % 2
        row = idx // 2
        xx, yy = lx + col * 420, ly + row * 56
        draw.rectangle((xx, yy + 5, xx + 30, yy + 35), fill=color, outline="#66747a")
        draw.text((xx + 44, yy), labels[key], font=font(26, zh=zh), fill=COLORS["muted"])
    low_max = low["outputs"]["maximum_depth_m"]
    high_max = high["outputs"]["maximum_depth_m"]
    note = (
        f"低情景最大水深 {low_max:.1f} m；高情景 {high_max:.1f} m；两个完成运行均未到达 3 个 CRISM 点。"
        if zh
        else f"Maximum depth: {low_max:.1f} m (low) and {high_max:.1f} m (high); neither completed run reached the three CRISM sites."
    )
    text_box(draw, note, (x0 + 42, y0 + 650), x1 - x0 - 84, font(25, zh=zh), COLORS["muted"], spacing=9)


def add_map_panel(canvas, image, box, label, caption, zh: bool):
    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = box
    rounded(draw, box, 22, "#ffffff", "#cbd3d6", 3)
    draw.text((x0 + 28, y0 + 24), label, font=font(36, bold=True, zh=zh), fill=COLORS["ink"])
    draw.text((x0 + 102, y0 + 28), caption, font=font(29, bold=True, zh=zh), fill=COLORS["ink"])
    im_x0, im_y0, im_x1, im_y1 = x0 + 24, y0 + 94, x1 - 24, y1 - 28
    fitted = image.resize((im_x1 - im_x0, im_y1 - im_y0), Image.Resampling.LANCZOS)
    canvas.paste(fitted, (im_x0, im_y0))


def make_science_figure(project: Path, release: Path, zh: bool) -> tuple[Path, Path]:
    out = completed_outputs(project)
    low = load_json(out / "low_summary.json")
    high = load_json(out / "high_summary.json")
    low_map = annotate_map(Image.open(out / "low_map.png"), zh)
    high_map = annotate_map(Image.open(out / "high_map.png"), zh)
    canvas = Image.new("RGB", (4800, 3000), "#f4f6f5")
    draw = ImageDraw.Draw(canvas)
    title = (
        "火星长期地下水出流：原二维模型的完成运行与水量收支"
        if zh
        else "Long-term Martian groundwater outflow: completed 2-D runs and water budgets"
    )
    subtitle = (
        "单一等效源代表两条概念沟槽的合计流量；沟槽位置不推测、不标绘；DEM 控制蓄水、溢流和开放边界外排。"
        if zh
        else "One equivalent source represents the combined discharge of two conceptual troughs; trough geometry is neither inferred nor drawn; DEM controls storage, spill and open-boundary outflow."
    )
    draw.text((100, 54), title, font=font(64, bold=True, zh=zh), fill=COLORS["ink"])
    draw.text((104, 145), subtitle, font=font(29, zh=zh), fill=COLORS["muted"])
    add_map_panel(
        canvas,
        low_map,
        (100, 230, 2365, 1900),
        "(a)",
        "低情景：恒定基流，10 年，C=0.4" if zh else "Low: constant baseflow, 10 yr, C=0.4",
        zh,
    )
    add_map_panel(
        canvas,
        high_map,
        (2435, 230, 4700, 1900),
        "(b)",
        "高情景：分阶段脉冲，30 年，C=1.0" if zh else "High: staged pulses, 30 yr, C=1.0",
        zh,
    )
    draw_curve_panel(draw, (100, 1970, 3200, 2900), zh)
    draw_budget_panel(draw, (3270, 1970, 4700, 2900), low, high, zh)
    footer = (
        "定量图仅使用 complete=true 且 paper_usable=true 的完成运行；中情景只在过程线中展示参数，不作为空间结果。"
        if zh
        else "Quantitative maps include only completed runs with complete=true and paper_usable=true; the medium scenario is shown only as a prescribed hydrograph, not as a spatial result."
    )
    draw.text((104, 2940), footer, font=font(24, zh=zh), fill="#6f7d82")
    stem = "论文图_完成运行对比_中文" if zh else "paper_figure_completed_runs_english"
    png = release / "assets" / "figures" / f"{stem}.png"
    tif = release / "assets" / "figures" / f"{stem}.tif"
    png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(png, dpi=(300, 300), optimize=True)
    canvas.save(tif, dpi=(300, 300), compression="tiff_lzw")
    return png, tif


def draw_control(draw, x, y, w, title, value, pct, accent="#69d9ff", zh=True):
    draw.text((x, y), title, font=font(23, zh=zh), fill="#dce9ed")
    tw = draw.textbbox((0, 0), value, font=font(23, bold=True, zh=zh))[2]
    draw.text((x + w - tw, y), value, font=font(23, bold=True, zh=zh), fill="#e6f8ff")
    draw.rounded_rectangle((x, y + 44, x + w, y + 56), 6, fill="#31434b")
    draw.rounded_rectangle((x, y + 44, x + max(10, w * pct), y + 56), 6, fill=accent)


def make_dashboard(project: Path, release: Path, zh: bool) -> tuple[Path, Path]:
    out = completed_outputs(project)
    high = load_json(out / "high_summary.json")
    map_image = annotate_map(Image.open(out / "high_map.png"), zh)
    canvas = Image.new("RGB", (4800, 3200), "#080d10")
    draw = ImageDraw.Draw(canvas)
    panel = (54, 42, 4746, 3158)
    rounded(draw, panel, 26, "#10191d", "#304149", 3)
    draw.rectangle((54, 42, 4746, 220), fill="#132026")
    title = "火星长期地下水出流与 DEM 控制积水模拟" if zh else "Long-term Martian groundwater outflow and DEM-controlled inundation"
    subtitle = (
        "原二维水动力模型 · 原始点位作为两条概念沟槽合计等效源 · 沟槽几何不推测、不标绘"
        if zh
        else "Original 2-D hydrodynamic model · one equivalent source for combined conceptual-trough discharge · no inferred trough geometry"
    )
    draw.text((100, 78), title, font=font(52, bold=True, zh=zh), fill="#edf5f7")
    draw.text((102, 150), subtitle, font=font(25, zh=zh), fill="#9fb1b9")
    draw.rounded_rectangle((4210, 93, 4650, 151), 29, fill="#1a313a", outline="#41606d", width=2)
    badge = "论文截图模式" if zh else "PAPER FIGURE MODE"
    bw = draw.textbbox((0, 0), badge, font=font(24, bold=True, zh=zh))[2]
    draw.text((4430 - bw / 2, 107), badge, font=font(24, bold=True, zh=zh), fill="#c8f2ff")

    button_y = 245
    buttons = (
        ("低情景" if zh else "Low", False),
        ("中情景" if zh else "Medium", False),
        ("高情景" if zh else "High", True),
        ("C=0.4", False),
        ("C=0.7", False),
        ("C=1.0", True),
    )
    x = 86
    for label, active in buttons:
        f = font(23, bold=active, zh=zh)
        w = draw.textbbox((0, 0), label, font=f)[2] + 42
        fill = "#d8f5ff" if active else "#1b282e"
        ink = "#0b1c23" if active else "#edf5f7"
        draw.rounded_rectangle((x, button_y, x + w, button_y + 54), 10, fill=fill, outline="#465960")
        draw.text((x + 21, button_y + 12), label, font=f, fill=ink)
        x += w + 14

    controls = (86, 330, 3080, 640)
    rounded(draw, controls, 16, "#162126", "#35474f", 2)
    labels = (
        ("出流过程线" if zh else "Hydrograph", "分阶段脉冲" if zh else "Staged pulses", 0.78),
        ("基流 Qb" if zh else "Baseflow Qb", "500 m³/s", 1.0),
        ("脉冲 Q0" if zh else "Pulse Q0", "5,000 m³/s", 1.0),
        ("持续时间 T" if zh else "Duration T", "30 yr", 0.60),
        ("沿程保留 C" if zh else "Retention C", "1.00", 1.0),
        ("当前总 Q(t)" if zh else "Current Q(t)", "500 m³/s", 0.10),
        ("累计原始出水" if zh else "Raw discharge", "837.9 km³", 0.84),
        ("自适应推进" if zh else "Adaptive stepping", "verified", 0.86),
    )
    cw, ch = 680, 110
    for idx, (lab, val, pct) in enumerate(labels):
        row, col = divmod(idx, 4)
        draw_control(draw, controls[0] + 36 + col * 730, controls[1] + 30 + row * 130, cw, lab, val, pct, zh=zh)

    map_box = (86, 680, 3080, 3090)
    rounded(draw, map_box, 16, "#090d0f", "#3a4a51", 2)
    fitted = map_image.resize((2946, 2368), Image.Resampling.LANCZOS)
    canvas.paste(fitted, (110, 695))

    side_x, side_w = 3120, 1590
    y = 330
    cards = [
        (360, "水量账本（完成运行）" if zh else "Water ledger (completed run)"),
        (300, "出水边界" if zh else "Source boundary"),
        (355, "CRISM 矿物点输出" if zh else "CRISM site outputs"),
        (300, "数值状态" if zh else "Numerical status"),
    ]
    for h, title_card in cards:
        rounded(draw, (side_x, y, side_x + side_w, y + h), 16, "#162126", "#35474f", 2)
        draw.text((side_x + 28, y + 24), title_card, font=font(27, bold=True, zh=zh), fill="#d8e7ec")
        if "水量" in title_card or "Water" in title_card:
            led = high["water_ledger_km3"]
            draw.text((side_x + 28, y + 82), f"{led['effective_after_c']:,.1f}", font=font(57, bold=True, zh=False), fill="#ecfbff")
            draw.text((side_x + 270, y + 111), "km³", font=font(25, zh=False), fill="#9fb1b9")
            values = (
                ("原始出水" if zh else "Raw", led["raw_release"]),
                ("源洼地" if zh else "Basin", led["source_basin_storage"]),
                ("域内水体" if zh else "Surface", led["downstream_surface_storage"]),
                ("边界外排" if zh else "Outflow", led["open_boundary_outflow"]),
            )
            for i, (lab, value) in enumerate(values):
                yy = y + 180 + i * 40
                draw.text((side_x + 28, yy), lab, font=font(23, zh=zh), fill="#9fb1b9")
                text = f"{value:,.1f} km³"
                tw = draw.textbbox((0, 0), text, font=font(23, bold=True, zh=False))[2]
                draw.text((side_x + side_w - 28 - tw, yy), text, font=font(23, bold=True, zh=False), fill="#edf5f7")
        elif "边界" in title_card or "Source" in title_card:
            rows = (
                ("固定点位" if zh else "Fixed source", "75.937180°E"),
                ("纬度" if zh else "Latitude", "18.136689°N"),
                ("Q 的含义" if zh else "Meaning of Q", "两沟槽合计" if zh else "combined total"),
                ("数值施加" if zh else "Application", "1 次" if zh else "once"),
                ("沟槽几何" if zh else "Trough geometry", "不标绘" if zh else "not drawn"),
            )
            for i, (lab, value) in enumerate(rows):
                yy = y + 82 + i * 40
                draw.text((side_x + 28, yy), lab, font=font(23, zh=zh), fill="#9fb1b9")
                tw = draw.textbbox((0, 0), value, font=font(23, bold=True, zh=zh))[2]
                draw.text((side_x + side_w - 28 - tw, yy), value, font=font(23, bold=True, zh=zh), fill="#edf5f7")
        elif "CRISM" in title_card:
            rows = (("C1", "Mg-carbonate"), ("P1", "Fe/Mg phyllosilicate"), ("A1", "Al-OH tentative"))
            for i, (site, mineral) in enumerate(rows):
                yy = y + 82 + i * 66
                draw.ellipse((side_x + 30, yy + 4, side_x + 46, yy + 20), fill=COLORS["crism"])
                draw.text((side_x + 62, yy), site, font=font(24, bold=True, zh=False), fill="#edf5f7")
                draw.text((side_x + 132, yy), mineral, font=font(22, zh=False), fill="#9fb1b9")
                draw.text((side_x + 1240, yy), "未到达" if zh else "not reached", font=font(22, zh=zh), fill="#f0c08c")
            draw.text((side_x + 30, y + 292), "覆盖 0 / 3" if zh else "Covered 0 / 3", font=font(27, bold=True, zh=zh), fill="#dff7ff")
        else:
            nums = high["numerics"]
            rows = (
                ("二维显式推进" if zh else "Explicit 2-D", f"{nums['explicit_surface_years']:.2f} yr"),
                ("验证稳态跳步" if zh else "Verified skip", f"{nums['verified_steady_skipped_years']:.2f} yr"),
                ("影子验证" if zh else "Shadow validation", f"{nums['steady_shadow_validations_passed']} passed"),
                ("质量误差" if zh else "Mass error", f"{nums['downstream_mass_error']:.2e}"),
                ("论文可用" if zh else "Paper usable", "是" if zh else "yes"),
            )
            for i, (lab, value) in enumerate(rows):
                yy = y + 82 + i * 40
                draw.text((side_x + 28, yy), lab, font=font(22, zh=zh), fill="#9fb1b9")
                tw = draw.textbbox((0, 0), value, font=font(22, bold=True, zh=zh))[2]
                draw.text((side_x + side_w - 28 - tw, yy), value, font=font(22, bold=True, zh=zh), fill="#edf5f7")
        y += h + 18

    rounded(draw, (side_x, y, side_x + side_w, 3090), 16, "#162126", "#35474f", 2)
    scope_title = "论文图使用边界" if zh else "Publication-use boundary"
    draw.text((side_x + 30, y + 28), scope_title, font=font(29, bold=True, zh=zh), fill="#d8e7ec")
    scope = (
        "点位严格采用模型 400 m 栅格行列号投影到 4× 结果图：源点 row=105, col=64；天然溢流口 row=103, col=84；C1/P1/A1 分别为 (149,167)、(154,168)、(142,155)。本图采用完成的高情景结果。未完成的中情景不作为空间定量结果。"
        if zh
        else "Markers are projected directly from model-grid indices to the 4× exact-run map: source row=105, col=64; spillway row=103, col=84; C1/P1/A1 at (149,167), (154,168) and (142,155). This panel uses the completed high scenario. The incomplete medium run is excluded from quantitative spatial interpretation."
    )
    text_box(draw, scope, (side_x + 30, y + 92), side_w - 60, font(28, zh=zh), "#9fb1b9", spacing=14)

    stem = "交互面板_论文截图_中文" if zh else "interactive_panel_paper_screenshot_english"
    png = release / "assets" / "figures" / f"{stem}.png"
    tif = release / "assets" / "figures" / f"{stem}.tif"
    canvas.save(png, dpi=(300, 300), optimize=True)
    canvas.save(tif, dpi=(300, 300), compression="tiff_lzw")
    return png, tif


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=REPO_ROOT)
    parser.add_argument("--release", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    products = []
    for zh in (True, False):
        products.extend(make_science_figure(args.project, args.release, zh))
        products.extend(make_dashboard(args.project, args.release, zh))
    paper = args.release / "paper_english"
    paper.mkdir(parents=True, exist_ok=True)
    figures = args.release / "assets" / "figures"
    for source_name, target_name in (
        ("interactive_panel_paper_screenshot_english.png", "Figure_1_interactive_model.png"),
        ("interactive_panel_paper_screenshot_english.tif", "Figure_1_interactive_model.tif"),
        ("paper_figure_completed_runs_english.png", "Figure_2_completed_runs.png"),
        ("paper_figure_completed_runs_english.tif", "Figure_2_completed_runs.tif"),
    ):
        shutil.copy2(figures / source_name, paper / target_name)
    print(json.dumps([str(path) for path in products], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
