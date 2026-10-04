# Design: Dynamic File Ingestion for Web Viewer

## 1. Architectural Overview
This feature extends the Web Viewer frontend (`web/index.html`, `web/css/viewer.css`, `web/js/main.js`) with two client-side ingestion pipelines:

```
[User Action]
   │
   ├─► Click "Load JSON" Button / File Picker ──┐
   ├─► Click "Load Video" Button / File Picker ─┤
   └─► Drag & Drop (JSON / Video files) ─────────┴─► [Drop Target / Router]
                                                           │
                      ┌────────────────────────────────────┴────────────────────────────────────┐
                      ▼                                                                         ▼
            [JSON Processor]                                                            [Video Processor]
          FileReader.readAsText                                                      URL.createObjectURL
                      │                                                                         │
                      ▼                                                                         ▼
           Validate & Parse Notes                                                    Set <video id="bg-video"> src
                      │                                                                         │
                      ▼                                                                         ▼
          app.loadNotesData(data)                                                   Synchronize Video Duration
       - Update renderer.notes                                                      - Update timeline max
       - Reset playback currentTime = 0                                             - Sync play/pause handlers
       - Update slider.max
       - Refresh track title display
```

## 2. UI Component Design

### 2.1 Toolbar Controls (`web/index.html`)
Hidden `<input type="file">` elements paired with stylish accessible button controls:
```html
<input type="file" id="input-load-json" accept=".json" style="display:none">
<input type="file" id="input-load-video" accept="video/*" style="display:none">

<button id="btn-load-json" class="btn-tool" title="Load custom notes JSON">📁 JSON読込</button>
<button id="btn-load-video" class="btn-tool" title="Load background video MP4/WebM">🎬 動画読込</button>
<span id="loaded-file-badge" class="badge-status">ray_notes.json</span>
```

### 2.2 Drag-and-Drop Overlay (`web/css/viewer.css`)
A full-screen dashed drop overlay that illuminates when files are dragged into the window:
```css
#drop-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.85);
  border: 3px dashed #38bdf8;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}
#drop-overlay.active {
  opacity: 1;
  pointer-events: auto;
}
```

## 3. Data & State Management (`web/js/main.js`)
- `handleJsonFile(file: File)`:
  - Invokes `FileReader.readAsText(file)`.
  - Parses JSON, verifies `payload.notes` is an array.
  - Updates `notes` array in `Renderer`, resets `currentTime` to 0, updates slider max to `payload.meta?.duration_sec` or calculated note end maximum.
  - Updates title text on UI.
- `handleVideoFile(file: File)`:
  - Creates Object URL `URL.createObjectURL(file)`.
  - Assigns to `bg-video.src`.
  - Adds event listener on `loadedmetadata` to set slider max and sync video duration.
