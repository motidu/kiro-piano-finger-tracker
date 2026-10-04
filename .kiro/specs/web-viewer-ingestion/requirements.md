# Requirements: Dynamic File Ingestion for Web Viewer

## 1. Overview
The Web Viewer currently defaults to loading `./data/ray_notes.json` upon initialization. To enable rapid evaluation of arbitrary piano performance videos and custom transcription JSON datasets without reloading or editing filesystem paths, the Web Viewer must provide direct file selection and drag-and-drop ingestion mechanisms.

## 2. Functional Requirements (EARS Notation)

### 2.1 JSON Data Ingestion
- **REQ-INGEST-01**: **When** the user clicks the "Load JSON" button, the system **shall** open a native file selection dialog filtering for `.json` files.
- **REQ-INGEST-02**: **When** a `.json` file is selected or dropped onto the window, the system **shall** parse the JSON using the browser `FileReader` API.
- **REQ-INGEST-03**: **Where** the parsed JSON contains a valid `notes` array, the system **shall** immediately update the renderer notes, reset playback to 0:00, update the timeline slider range to match `duration_sec` or maximum note end time, and update the UI title label.
- **REQ-INGEST-04**: **Where** the selected file is malformed or missing note data, the system **shall** display a descriptive error toast without crashing the rendering loop.

### 2.2 Video File Ingestion
- **REQ-INGEST-05**: **When** the user clicks the "Load Video" button, the system **shall** open a native file selection dialog filtering for video files (`video/*`).
- **REQ-INGEST-06**: **When** a video file is selected or dropped, the system **shall** generate a local object URL using `URL.createObjectURL(file)` and set it as the background `<video>` element source.
- **REQ-INGEST-07**: **When** the video metadata is loaded, the system **shall** synchronize the timeline maximum duration with the video duration and align Canvas overlay dimensions.

### 2.3 Drag-and-Drop Interaction
- **REQ-INGEST-08**: **While** a file is being dragged over the application window, the system **shall** display an active visual overlay ("Drop JSON or Video here").
- **REQ-INGEST-09**: **When** files are dropped onto the window, the system **shall** automatically detect whether each file is JSON or Video based on MIME type or extension and invoke the corresponding ingestion pipeline.

## 3. Non-Functional Requirements
- **NFR-PERF-01**: Ingestion and schema swap must occur within 100ms without freezing the 60fps requestAnimationFrame loop.
- **NFR-SEC-01**: All operations must execute client-side using native Web APIs without sending user media or files to external networks.
