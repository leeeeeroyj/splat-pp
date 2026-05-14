#!/usr/bin/env python3
"""
splat-pp-tui.py — Splatoon 3 Post Printer TUI
A Textual-based terminal UI wrapper around splat-pp.py.

Install deps:
    pip install textual pillow numpy

Run:
    python splat-pp-tui.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import (
        Button, Footer, Header, Input, Label, ListItem, ListView,
        RichLog, Static,
    )
    from textual.reactive import reactive
    from rich.text import Text
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("Missing dependency: pip install textual")
    sys.exit(1)

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Missing dependency: pip install pillow numpy")
    sys.exit(1)

# ── Import splat-pp logic (no modification to original file) ──────────────────
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    import importlib.util, types
    spec = importlib.util.spec_from_file_location("splat_pp", SCRIPT_DIR / "splat-pp.py")
    splat_pp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(splat_pp)
except Exception as e:
    splat_pp = None
    _IMPORT_ERROR = str(e)
else:
    _IMPORT_ERROR = None

IMG_DIR = SCRIPT_DIR / "img"

# ── Splatoon palette ──────────────────────────────────────────────────────────
INK_YELLOW  = "#F6E229"
INK_GREEN   = "#3BC335"
INK_ORANGE  = "#F55F00"
INK_PINK    = "#E64E8C"
INK_TEAL    = "#19D4C8"
INK_DARK    = "#1A1A2E"
INK_DARKER  = "#0D0D1A"
PANEL_BG    = "#16213E"

# ── ASCII splash art ──────────────────────────────────────────────────────────
SPLASH_ART = r"""
[bold #F6E229]
  ███████╗██████╗ ██╗      █████╗ ████████╗        ██████╗  ██████╗ 
  ██╔════╝██╔══██╗██║     ██╔══██╗╚══██╔══╝       ██╔══██╗ ██╔══██╗
  ███████╗██████╔╝██║     ███████║   ██║    ████╗ ██████╔╝ ██████╔╝
  ╚════██║██╔═══╝ ██║     ██╔══██║   ██║    ╚═══╝ ██╔═══╝  ██╔═══╝ 
  ███████║██║     ███████╗██║  ██║   ██║          ██║      ██║     
  ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝          ╚═╝      ╚═╝     
[/bold #F6E229]"""

SPLASH_SUB = "[bold #3BC335]  Splatoon 3 Plaza Post Printer[/bold #3BC335] \n [dim #F6E229]  by …LEEEEROYJ [/dim #F6E229]"

SPLAT_DECO = "[#F55F00]  ╰( ◕ ᗜ ◕ )╮ ✦ ✦ ✦  Ink it up, squids! ✦ ✦ ✦[/#F55F00]"

CSS = f"""
Screen {{
    background: {INK_DARKER};
}}

/* ── Splash ── */
#splash-screen {{
    align: center middle;
    background: {INK_DARKER};
}}
#splash-art {{
    content-align: center middle;
    width: 100%;
    padding: 1 0;
}}
#splash-sub {{
    content-align: center middle;
    width: 100%;
    padding: 0 0 1 0;
}}
#splash-deco {{
    content-align: center middle;
    width: 100%;
    padding: 0 0 2 0;
}}
#splash-hint {{
    content-align: center middle;
    width: 100%;
    color: {INK_TEAL};
    text-style: bold;
}}
#splash-border {{
    border: double {INK_YELLOW};
    padding: 2 4;
    margin: 2 8;
    background: {INK_DARK};
}}

/* ── Image select ── */
#img-screen {{
    background: {INK_DARKER};
}}
#img-title {{
    background: {INK_YELLOW};
    color: {INK_DARK};
    text-style: bold;
    content-align: center middle;
    height: 3;
    width: 100%;
    padding: 0 2;
}}
#img-list-container {{
    border: round {INK_GREEN};
    margin: 1 4;
    height: 1fr;
    background: {INK_DARK};
}}
#img-list {{
    background: {INK_DARK};
}}
#img-list > ListItem {{
    color: #FFFFFF;
    padding: 0 2;
    background: {INK_DARK};
}}
#img-list > ListItem.--highlight {{
    background: {INK_YELLOW};
    color: {INK_DARK};
    text-style: bold;
}}
#img-hint {{
    content-align: center middle;
    color: {INK_TEAL};
    height: 3;
    text-style: italic;
}}
#img-none {{
    content-align: center middle;
    color: {INK_ORANGE};
    height: 5;
    text-style: bold;
}}

/* ── Params ── */
#params-screen {{
    background: {INK_DARKER};
}}
#params-title {{
    background: {INK_GREEN};
    color: {INK_DARK};
    text-style: bold;
    content-align: center middle;
    height: 3;
    width: 100%;
    padding: 0 2;
}}
#params-box {{
    border: round {INK_YELLOW};
    margin: 1 4;
    padding: 1 2;
    background: {INK_DARK};
    height: auto;
}}
.param-label {{
    color: {INK_YELLOW};
    text-style: bold;
    padding: 1 0 0 0;
}}
.param-desc {{
    color: #888888;
    text-style: italic;
    padding: 0 0 0 2;
}}
.param-input {{
    border: round {INK_TEAL};
    background: {INK_DARKER};
    color: #FFFFFF;
    margin: 0 0 0 2;
    width: 20;
}}
#params-actions {{
    margin: 1 4;
    height: auto;
    align: center middle;
}}
#btn-go {{
    background: {INK_YELLOW};
    color: {INK_DARK};
    text-style: bold;
    border: none;
    margin: 0 2;
    padding: 0 4;
    min-width: 20;
}}
#btn-go:hover {{
    background: {INK_GREEN};
}}
#btn-back {{
    background: {INK_DARK};
    color: {INK_TEAL};
    border: round {INK_TEAL};
    margin: 0 2;
    padding: 0 4;
    min-width: 12;
}}
#btn-back:hover {{
    background: {INK_TEAL};
    color: {INK_DARK};
}}
#params-summary {{
    color: #AAAAAA;
    content-align: center middle;
    margin: 0 4 1 4;
    height: 3;
    text-style: italic;
}}

/* ── Run ── */
#run-screen {{
    background: {INK_DARKER};
}}
#run-title {{
    background: {INK_ORANGE};
    color: #FFFFFF;
    text-style: bold;
    content-align: center middle;
    height: 3;
    width: 100%;
    padding: 0 2;
}}
#run-log {{
    border: round {INK_GREEN};
    margin: 1 4;
    height: 1fr;
    background: {INK_DARK};
}}
#run-status {{
    content-align: center middle;
    height: 3;
    color: {INK_TEAL};
    text-style: bold;
}}
#btn-done {{
    background: {INK_GREEN};
    color: {INK_DARK};
    text-style: bold;
    border: none;
    padding: 0 4;
    min-width: 20;
    display: none;
}}
#btn-done:hover {{
    background: {INK_YELLOW};
}}
#run-actions {{
    align: center middle;
    height: 3;
    margin: 0 0 1 0;
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Screen 1: Splash
# ─────────────────────────────────────────────────────────────────────────────
class SplashScreen(Screen):
    BINDINGS = [Binding("enter", "proceed", "Continue"), Binding("space", "proceed", "Continue")]

    def compose(self) -> ComposeResult:
        with Container(id="splash-screen"):
            with Container(id="splash-border"):
                yield Static(SPLASH_ART, id="splash-art", markup=True)
                yield Static(SPLASH_SUB, id="splash-sub", markup=True)
                yield Static(SPLAT_DECO, id="splash-deco", markup=True)
                yield Static(
                    f"[blink][ PRESS ANY KEY TO CONTINUE ][/blink]",
                    id="splash-hint",
                    markup=True,
                )

    def on_key(self, event) -> None:
        event.stop()
        self.app.push_screen(ImageSelectScreen())


# ─────────────────────────────────────────────────────────────────────────────
# Screen 2: Image Select
# ─────────────────────────────────────────────────────────────────────────────
class ImageSelectScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("enter", "select_image", "Select"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("🦑  SELECT YOUR IMAGE  🦑", id="img-title")
        images = self._find_images()
        if images:
            items = [ListItem(Label(f"  {self._format_item(img)}"), name=str(img)) for img in images]
            with ScrollableContainer(id="img-list-container"):
                yield ListView(*items, id="img-list")
            yield Static(
                f"[{INK_TEAL}]↑ ↓ to browse  ·  Enter to select  ·  Esc to go back[/{INK_TEAL}]",
                id="img-hint",
                markup=True,
            )
        else:
            yield Static(
                f"[{INK_ORANGE}]No PNG files found in img/\n\nDrop some images in the img/ folder and restart![/{INK_ORANGE}]",
                id="img-none",
                markup=True,
            )

    def _find_images(self) -> list[Path]:
        if not IMG_DIR.exists():
            return []
        return sorted(IMG_DIR.glob("*.png")) + sorted(IMG_DIR.glob("*.PNG"))

    def _format_item(self, path: Path) -> str:
        try:
            img = Image.open(path)
            w, h = img.size
            import numpy as np
            arr = np.array(img.convert("L")) < 128
            pct = arr.sum() / arr.size * 100
            return f"{path.name:<30}  {w}×{h}  [{pct:.0f}% black]"
        except Exception:
            return path.name
    
    def on_mount(self) -> None:
        try:
            lv = self.query_one("#img-list", ListView)
            lv.focus()
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected_path = Path(event.item.name)
        self.app.push_screen(ParamsScreen(selected_path))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_select_image(self) -> None:
        lv = self.query_one("#img-list", ListView)
        if lv.highlighted_child:
            selected_path = Path(lv.highlighted_child.name)
            self.app.push_screen(ParamsScreen(selected_path))


# ─────────────────────────────────────────────────────────────────────────────
# Screen 3: Params
# ─────────────────────────────────────────────────────────────────────────────
class ParamsScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, image_path: Path):
        super().__init__()
        self.image_path = image_path

    def compose(self) -> ComposeResult:
        yield Static(f"🎨  CONFIGURE: {self.image_path.name}  🎨", id="params-title")
        with Container(id="params-box"):
            yield Label("Duration (ms per action)", classes="param-label")
            yield Label("Lower = faster but riskier. Range: 20–200. Default: 25", classes="param-desc")
            yield Input(value="25", id="input-duration", classes="param-input")

            yield Label("Template file", classes="param-label")
            yield Label("Path to .txt sketch template. Default: sketch.txt", classes="param-desc")
            yield Input(value="sketch.txt", id="input-template", classes="param-input")

        yield Static("", id="params-summary")

        with Horizontal(id="params-actions"):
            yield Button("◀  Back", id="btn-back", variant="default")
            yield Button("▶  INK IT!  🦑", id="btn-go", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-go":
            self._launch()
        elif event.button.id == "btn-back":
            self.action_go_back()

    def _launch(self) -> None:
        duration_str = self.query_one("#input-duration", Input).value.strip()
        template_str = self.query_one("#input-template", Input).value.strip()
        summary = self.query_one("#params-summary", Static)

        try:
            duration = int(duration_str)
            if not (20 <= duration <= 200):
                raise ValueError
        except ValueError:
            summary.update(f"[{INK_ORANGE}]⚠ Duration must be an integer between 20 and 200![/{INK_ORANGE}]")
            return

        template_path = Path(template_str)
        if not template_path.exists():
            summary.update(f"[{INK_ORANGE}]⚠ Template not found: {template_str}[/{INK_ORANGE}]")
            return

        self.app.push_screen(RunScreen(self.image_path, duration, template_path))

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ─────────────────────────────────────────────────────────────────────────────
# Screen 4: Run (compile + flash)
# ─────────────────────────────────────────────────────────────────────────────
class RunScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back (after run)")]

    def __init__(self, image_path: Path, duration: int, template_path: Path):
        super().__init__()
        self.image_path = image_path
        self.duration = duration
        self.template_path = template_path

    def compose(self) -> ComposeResult:
        yield Static(f"🚀  PRINTING: {self.image_path.name}  🚀", id="run-title")
        yield RichLog(id="run-log", highlight=True, markup=True, wrap=True)
        yield Static("", id="run-status")
        with Horizontal(id="run-actions"):
            yield Button("✅  Done! Start over", id="btn-done", variant="success")

    def on_mount(self) -> None:
        self.run_worker(self._run_pipeline(), exclusive=True)

    def run_worker(self, coro, exclusive=False):
        self.app.call_after_refresh(lambda: asyncio.ensure_future(coro))

    async def _run_pipeline(self) -> None:
        log = self.query_one("#run-log", RichLog)
        status = self.query_one("#run-status", Static)

        def info(msg):  log.write(Text.from_markup(f"[bold {INK_TEAL}]›[/bold {INK_TEAL}] {msg}"))
        def ok(msg):    log.write(Text.from_markup(f"[bold {INK_GREEN}]✓[/bold {INK_GREEN}] {msg}"))
        def warn(msg):  log.write(Text.from_markup(f"[bold {INK_YELLOW}]⚠[/bold {INK_YELLOW}] {msg}"))
        def err(msg):   log.write(Text.from_markup(f"[bold {INK_ORANGE}]✗[/bold {INK_ORANGE}] {msg}"))
        def raw(msg):   log.write(Text(msg, style="dim"))

        if splat_pp is None:
            err(f"Failed to import splat-pp.py: {_IMPORT_ERROR}")
            status.update(f"[{INK_ORANGE}]Import failed — check that splat-pp.py is in the same directory.[/{INK_ORANGE}]")
            return

        status.update(f"[{INK_YELLOW}]⏳  Running…  Squids are working hard![/{INK_YELLOW}]")

        try:
            # ── Load image ────────────────────────────────────────────────────
            info(f"Loading image: [bold]{self.image_path}[/bold]")
            await asyncio.sleep(0.05)
            black = await asyncio.get_event_loop().run_in_executor(
                None, splat_pp.load_image, str(self.image_path)
            )
            pixel_count = int(black.sum())
            ok(f"Black pixels: [bold]{pixel_count:,}[/bold] / {splat_pp.CANVAS_W * splat_pp.CANVAS_H:,}")

            # ── Plan moves ────────────────────────────────────────────────────
            info("Planning snake-scan move sequence…")
            await asyncio.sleep(0.05)
            pixels = await asyncio.get_event_loop().run_in_executor(
                None, splat_pp.plan_moves, black
            )
            ok(f"Draw operations: [bold]{len(pixels):,}[/bold]")

            # ── Encode bytecode ───────────────────────────────────────────────
            info("Encoding bytecode…")
            await asyncio.sleep(0.05)
            bytecode = await asyncio.get_event_loop().run_in_executor(
                None, splat_pp.encode_bytecode, pixels
            )
            actions = splat_pp.count_actions(bytecode)
            est_s = (actions * self.duration * 2) / 1000
            ok(f"Bytecode size: [bold]{len(bytecode):,} bytes[/bold]")
            ok(f"Estimated draw time: [bold]{est_s:.0f}s ({est_s/60:.1f} min)[/bold]")

            # ── Generate sketch ───────────────────────────────────────────────
            info("Generating sketch…")
            await asyncio.sleep(0.05)
            draw_fn = splat_pp.generate_draw_function(
                bytecode, pixel_count, self.duration, self.image_path.name, actions
            )
            full_sketch = splat_pp.generate_full_sketch(str(self.template_path), draw_fn)
            base_name = self.image_path.stem
            sketch_dir = splat_pp.SKETCH_DIR / base_name
            sketch_dir.mkdir(parents=True, exist_ok=True)
            out_path = sketch_dir / f"{base_name}.ino"
            out_path.write_text(full_sketch, encoding="utf-8")
            ok(f"Written to: [bold]{out_path}[/bold]")

            # ── Compile ───────────────────────────────────────────────────────
            info("Compiling with arduino-cli…")
            await asyncio.sleep(0.05)
            splat_pp.BUILD_DIR.mkdir(parents=True, exist_ok=True)
            proc = await asyncio.create_subprocess_exec(
                "arduino-cli", "compile",
                "--fqbn", splat_pp.FQBN,
                "--build-path", str(splat_pp.BUILD_DIR),
                str(sketch_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            for line in stdout.decode().splitlines():
                if "Sketch uses" in line or "Global variables" in line:
                    ok(line.strip())
                elif line.strip():
                    raw(line.strip())
            if proc.returncode != 0:
                for line in stderr.decode().splitlines():
                    err(line)
                raise RuntimeError("Compile failed")
            ok("Compile successful!")

            hex_file = splat_pp.BUILD_DIR / f"{base_name}.ino.hex"
            if not hex_file.exists():
                raise RuntimeError(f"Hex file not found: {hex_file}")

            # ── Flash ─────────────────────────────────────────────────────────
            log.write("")
            log.write(Text.from_markup(
                f"[bold {INK_YELLOW}]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold {INK_YELLOW}]"
            ))
            log.write(Text.from_markup(
                f"[bold {INK_YELLOW}]  Ready to flash![/bold {INK_YELLOW}]"
            ))
            log.write(Text.from_markup(
                f"[{INK_TEAL}]  Press the button on your Teensy 4.0, then press Enter here…[/{INK_TEAL}]"
            ))
            log.write(Text.from_markup(
                f"[bold {INK_YELLOW}]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold {INK_YELLOW}]"
            ))

            status.update(f"[bold {INK_YELLOW}]⚡  Waiting for Teensy button press — then press Enter in terminal…[/bold {INK_YELLOW}]")

            # Run teensy_loader_cli (blocking — it waits for device)
            await asyncio.get_event_loop().run_in_executor(
                None, self._do_flash, hex_file, log
            )

            # ── Cleanup ───────────────────────────────────────────────────────
            import shutil
            if splat_pp.BUILD_DIR.exists():
                shutil.rmtree(splat_pp.BUILD_DIR)
            ok("Build directory cleaned up.")

            log.write("")
            log.write(Text.from_markup(
                f"[bold {INK_GREEN}]🦑  ALL DONE!  Connect your Teensy to the Switch and head to the plaza post printer![/bold {INK_GREEN}]"
            ))
            status.update(f"[bold {INK_GREEN}]✅  Done! Your ink is ready to flow.[/bold {INK_GREEN}]")

        except Exception as exc:
            err(f"Error: {exc}")
            status.update(f"[bold {INK_ORANGE}]❌  Something went wrong. Check the log above.[/bold {INK_ORANGE}]")

        finally:
            done_btn = self.query_one("#btn-done", Button)
            done_btn.styles.display = "block"

    def _do_flash(self, hex_file, log):
        """Blocking flash call (runs in executor so TUI stays responsive)."""
        import threading
        result = subprocess.run(
            [
                "teensy_loader_cli",
                f"--mcu={splat_pp.MCU}",
                "-w", "-v",
                str(hex_file),
            ],
            capture_output=True,
            text=True,
        )
        def _write():
            rlog = self.query_one("#run-log", RichLog)
            for line in result.stdout.splitlines():
                rlog.write(Text(line, style=f"dim {INK_TEAL}"))
            if result.returncode != 0:
                for line in result.stderr.splitlines():
                    rlog.write(Text.from_markup(f"[{INK_ORANGE}]✗ {line}[/{INK_ORANGE}]"))
                raise RuntimeError("Flash failed")
        import asyncio as _aio
        _aio.get_event_loop().call_soon_threadsafe(_write)
        if result.returncode != 0:
            raise RuntimeError("Flash failed")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-done":
            # Pop back to splash
            self.app.pop_screen()
            self.app.pop_screen()
            self.app.pop_screen()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ─────────────────────────────────────────────────────────────────────────────
# App root
# ─────────────────────────────────────────────────────────────────────────────
class SplatPPApp(App):
    CSS = CSS
    TITLE = "SPLAT-PP"
    SUB_TITLE = "Splatoon 3 Plaza Post Printer"
    BINDINGS = [Binding("ctrl+c", "quit", "Quit")]

    def on_mount(self) -> None:
        self.push_screen(SplashScreen())


def main():
    app = SplatPPApp()
    app.run()


if __name__ == "__main__":
    main()