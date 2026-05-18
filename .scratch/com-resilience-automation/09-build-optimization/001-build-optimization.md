# Final Build Optimization: Headless Chromium, Size Validation, UPX Evaluation

## What to build

Optimize the bundle after operational correctness is proven (Slice 8 passes). This is the final packaging step.

**Steps:**

1. **Measure actual bundle size** with current --onedir + headless Chromium
2. **Pin Playwright and Chromium versions** in `requirements-lock.txt`
   - Minimum Playwright 1.40+
   - Document exact Chromium revision
3. **Headless Chromium tuning:**
   - Verify headless shell (not full Chromium) is being used
   - If bundle exceeds 100-120MB target, investigate which assets can be trimmed
4. **Optional UPX evaluation** (configurable in build pipeline):
   - Benchmark compression ratio on the EXE
   - Measure startup penalty
   - Evaluate AV false-positive risk
   - Do NOT enable UPX by default — make it a configurable build variant
   - Support both compressed and uncompressed release variants
5. **Final build scripts:**
   - `build.ps1` — production build with pinned versions
   - `build-compressed.ps1` (optional) — UPX variant
   - Verify reproducible builds (same source → same output)

**Documentation to produce:**
- Playwright version
- Chromium revision
- Tested Windows versions
- Tested Outlook versions
- Bundle size measurements

**Optional validation checkpoint (HITL-light):**
- If UPX is considered, review measured AV detection rates before enabling
- This is execution-time validation, not a design decision

**Interface contract:**
- Input: validated codebase (Slice 8 passes), build.ps1
- Output: production-ready package, size within target, documentation
- Depends on: 08-pdf-validation.md

## Acceptance criteria

- [ ] Actual bundle size is measured and documented
- [ ] Playwright version is pinned to 1.40+ in requirements-lock.txt
- [ ] Chromium revision is pinned and documented
- [ ] Headless shell (not full Chromium) is confirmed in use
- [ ] Bundle size is within target range (100-120MB) or documented deviation
- [ ] UPX evaluation is performed with measurements (optional enablement)
- [ ] Build scripts produce reproducible output
- [ ] Tested Windows/Outlook version combinations are documented

## Blocked by

- 08-pdf-validation.md