# Implementation Tasks: Dynamic File Ingestion for Web Viewer

- [ ] Task 1: UI Structure & Controls (`web/index.html`)
  - [ ] Add hidden `<input type="file" id="input-load-json" accept=".json">`
  - [ ] Add hidden `<input type="file" id="input-load-video" accept="video/*">`
  - [ ] Add toolbar buttons `#btn-load-json` and `#btn-load-video`
  - [ ] Add status indicator `#loaded-file-badge` showing currently loaded dataset name
  - [ ] Add `#drop-overlay` markup for drag-and-drop visual indicator

- [ ] Task 2: Stylesheet Enhancements (`web/css/viewer.css`)
  - [ ] Style `#btn-load-json` and `#btn-load-video` buttons
  - [ ] Style `#loaded-file-badge`
  - [ ] Style `#drop-overlay` with modern backdrop blur and animated border

- [ ] Task 3: Logic Implementation (`web/js/main.js`)
  - [ ] Wire up button click handlers to trigger respective `<input type="file">.click()`
  - [ ] Implement `handleJsonFile(file)` parsing `FileReader` and reloading notes dynamically
  - [ ] Implement `handleVideoFile(file)` attaching `URL.createObjectURL(file)` to `<video>`
  - [ ] Implement window-level `dragover`, `dragleave`, and `drop` event listeners
  - [ ] Router in `drop` listener routing `.json` to `handleJsonFile` and video files to `handleVideoFile`

- [ ] Task 4: Verification
  - [ ] Verify JS syntax via `node --check web/js/main.js`
  - [ ] Test with sample JSON and verify smooth switching without reload
