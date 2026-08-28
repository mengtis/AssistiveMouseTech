# AssistiveMouseTech

**A webcam is the only hardware you need to control a computer.**

AssistiveMouseTech turns any standard laptop camera into a full mouse — cursor movement, left/right click, drag, and scroll — driven entirely by hand position and hand gestures. No touchpad. No stylus. No wearable sensor. No eye tracker. No purpose-built assistive hardware of any kind.

It is built for people who cannot reliably use a conventional pointing device: users with limited fine motor control, tremor, repetitive strain injury, limb difference, spinal cord injury, or progressive neuromuscular conditions such as ALS and muscular dystrophy.

<!-- TODO: replace with a real GIF/screencast of the cursor being driven by hand. Officers and reviewers watch the demo first. -->
**Demo video:** https://youtu.be/ekWOpIs6XiM (OpenCV pipeline — calibration, tracking, and cursor control)

---

## Why this matters

Commercial assistive pointing devices — head trackers, eye-gaze bars, sip-and-puff switches, adaptive trackballs — routinely cost hundreds to thousands of dollars, often require clinical fitting, and are not portable between machines. That cost is the barrier, not the technology.

Roughly **1 in 4 U.S. adults lives with a disability, and mobility impairment is the most commonly reported type** ([CDC, Disability Impacts All of Us](https://www.cdc.gov/ncbddd/disabilityandhealth/infographic-disability-impacts-all.html)). The overwhelming majority of those users already own the one piece of hardware this project needs: a webcam.

AssistiveMouseTech is released as **free and open source** so that the capability is reproducible by anyone — a clinician, a researcher, a caregiver, or a developer building the next accessibility tool — without licensing a proprietary SDK or buying dedicated hardware.

---

## Impact and reuse

> **NOTE TO MAINTAINER — fill this table in with verifiable numbers before using this README as an exhibit.**
> Do not estimate. Pull real figures from the GitHub Insights tab (stars, forks, unique cloners, traffic),
> Google Scholar, and your own records. Every row below should be independently checkable by a third party.

| Evidence of impact | Figure | Where to verify |
| --- | --- | --- |
| GitHub stars | _TODO_ | Repository landing page |
| Forks / downstream derivative repos | _TODO_ | GitHub "Forks" / "Used by" |
| Unique repository cloners (14-day window) | _TODO_ | Insights → Traffic |
| External contributors | _TODO_ | Insights → Contributors |
| Issues / pull requests from outside users | _TODO_ | Issues and PR tabs |
| Academic citations or course use | _TODO_ | Google Scholar, syllabi |
| Press, talks, or demo showings | _TODO_ | Links to coverage |
| Labeled gesture samples publicly released | **19,932** | `gesture_learning/data/` (verified by line count) |
| Custom MediaPipe C++ operators contributed | **6** | `mediapipe/mediapipe/calculators/util/` |

**What is genuinely reusable by others, independent of this application:**

1. **Six custom MediaPipe C++ calculators** that extend Google's MediaPipe framework with gesture classification, hand segmentation, and IPC egress. These are general-purpose graph nodes — any MediaPipe project can drop them in.
2. **An open, language-agnostic streaming interface.** Hand landmarks and tracking state are published over plain UDP and a named FIFO in a documented text format ([see below](#open-integration-interface)). Any program in any language on any OS can consume the hand-tracking stream without linking against this codebase. This is the difference between a demo and infrastructure.
3. **19,932 labeled hand-gesture samples** across four progressively harder class taxonomies (2, 3, 4, and 5 classes), plus the feature-engineering code that turns raw landmarks into rotation- and scale-invariant descriptors.
4. **A reproducible accessibility benchmark suite** — quantitative, repeatable tests for pointing accuracy, click accuracy, and drag-selection ([see below](#reproducible-evaluation-harness)). Assistive-input research is chronically hard to compare across papers because everyone invents their own ad-hoc test; these scripts are a shared yardstick.
5. **A paired ground-truth dataset** (`data/groundtruth/*.mp4` with matching `data/mediapipe_output/*.csv`) so that any change to the tracking pipeline can be regression-tested against recorded human motion instead of re-filmed by hand.

---

## Two independent pipelines, deliberately

Most gesture-control projects pick one tracking backend and inherit its limitations. This project ships two complete implementations with an explicit engineering trade-off between them, so a deployment can choose based on the user's hardware rather than the author's preference.

| | **MediaPipe pipeline** | **OpenCV pipeline** |
| --- | --- | --- |
| Tracking method | 21-point hand landmark model | HSV colour segmentation + motion tracking |
| Gesture vocabulary | Rich — full hand geometry | Limited — position and coarse shape |
| Throughput | Lower; GPU/CPU intensive | **Full 30 FPS** on commodity CPU |
| Portability | Linux only (Bazel toolchain) | **Windows and Linux** (macOS blocked, see below) |
| Setup burden | Build from source | `pip install -r requirements.txt`, run |
| Best for | Expressive multi-gesture control | Low-power machines, broad deployment |

Building both is the point: the MediaPipe path proves the ceiling of what gesture control can express, and the OpenCV path proves it can ship to a user on a five-year-old laptop today.

---

## Architecture

```
                    ┌──────────────┐
                    │   Webcam     │  (or Intel RealSense depth camera)
                    └──────┬───────┘
                           │ frames
        ┌──────────────────┴──────────────────┐
        │                                     │
┌───────▼─────────┐                 ┌─────────▼──────────┐
│ MediaPipe graph │                 │  OpenCV pipeline   │
│  (C++, Linux)   │                 │  (Python, cross-OS)│
├─────────────────┤                 ├────────────────────┤
│ hand landmarks  │                 │ HSV segmentation   │
│ frame reduction │                 │ hand tracker       │
│ gesture detect  │                 │ (predictive ROI)   │
│ centroid calc   │                 └─────────┬──────────┘
└───────┬─────────┘                           │
        │ UDP :2000/:3000/:4000                │ hand position
        │ FIFO "Mouse"                         │
        └──────────────────┬───────────────────┘
                           │
                 ┌─────────▼──────────┐
                 │ Filtering (IIR/FIR)│  ← tremor / jitter suppression
                 └─────────┬──────────┘
                           │
                 ┌─────────▼──────────┐
                 │ Control state m/c  │  OUT_OF_RANGE ⇄ IN_RANGE ⇄ DRAG
                 └─────────┬──────────┘
                           │
                 ┌─────────▼──────────┐
                 │  OS cursor + click │
                 └────────────────────┘
```

The separation of **tracking → filtering → control → actuation** is what makes the system adaptable. A user with tremor changes only the filter stage; a user on Windows changes only the actuation stage; a researcher testing a new hand detector replaces only the tracking stage.

---

## Technical contributions

### 1. Frame-reduction for real-time viability
Landmark inference is the bottleneck. The MediaPipe graph was modified to process a reduced frame stream while the downstream cursor controller interpolates the skipped frames, keeping perceived cursor latency low without paying full inference cost on every frame. The mouse controller is explicitly synchronised to this scheme (`mouse-control-test/mouse_control_for_demo1_with_new_gesures.py`).

### 2. Geometry-based gesture recognition in C++
`gesture_detection_new_calculator.cc` classifies gestures directly from hand geometry — inter-finger angles, cosine/sine of landmark vectors, and a rotation matrix derived from the palm axis — rather than from a second neural network. This runs inside the MediaPipe graph at frame rate with no additional model load. An earlier, simpler version (`gesture_detection_calculator.cc`) that merely counted extended fingers is retained for comparison, documenting the evolution of the approach.

### 3. Rotation- and scale-invariant landmark features
`gesture_learning/learn.py` derives augmented features from raw landmarks — extended-finger counts, pairwise inter-finger angles, and normalised inter-joint distance ratios — so a gesture classifies identically whether the hand is near or far, tilted or upright. Raw pixel coordinates cannot do this; the normalisation is what makes the models usable across different users and camera distances.

### 4. Classical and deep models, compared honestly
KMeans, Gaussian Mixture Models, Random Forest, and a Keras DNN are all implemented and evaluated on the same features (`gesture_learning/`, plus Jupyter notebooks with the runs preserved). Random Forest is the deployed choice; models are serialised to joblib/H5 so they can be loaded directly inside the MediaPipe pipeline.

<!-- TODO: populate with the real measured numbers from your capstone report. Do not round up. -->
| Model | Classes | Validation accuracy |
| --- | --- | --- |
| Random Forest | _TODO_ | _TODO_ |
| Gaussian Mixture | _TODO_ | _TODO_ |
| KMeans | _TODO_ | _TODO_ |
| Deep NN (Keras) | _TODO_ | _TODO_ |

### 5. Predictive region-of-interest tracking
The OpenCV tracker (`cameramouse/hand_tracking/tracking.py`) maintains hand position *and velocity*, then searches only a small predicted subregion of the next frame instead of the whole image. This is what buys the full 30 FPS on a CPU-only machine.

### 6. Tremor-aware filtering and an explicit control state machine
`cameramouse/control/filters.py` implements IIR and FIR filters over the hand position stream to suppress involuntary motion — directly targeting users with tremor. `cameramouse/control/mouse_states.py` implements the OUT_OF_RANGE / IN_RANGE / DRAG state machine, so a user can rest their hand, or leave frame, without the cursor running away — a failure mode that makes naive gesture mice unusable in practice.

### 7. C++ port for pipeline integration
`colour_segmentation_cpp/` re-implements the Python segmentation in C++ specifically so the OpenCV tracker could be fused into the MediaPipe graph (`hand_tracking_calculator.cc`), enabling automatic skin-tone calibration from MediaPipe's own hand detection instead of asking the user to hold a hand in a green box.

---

## Quick start

### OpenCV pipeline (recommended first run — Windows / Linux)

```bash
python3 -m pip install -r requirements.txt

cd cameramouse
python3 main.py
```

> **macOS is not currently supported.** `hardware/monitor.py` and
> `hardware/mouse.py` fall back to the `mouse` package off Windows, and that
> package ships Windows and Linux backends only — on Darwin it raises
> `OSError: Unsupported platform 'Darwin'` at import time, so `main.py` cannot
> start. `pip install` itself succeeds (the dependency is marked
> `sys_platform != "darwin"`); it is the import that fails. Routing the
> fallback through `pyautogui`, already a dependency and Darwin-capable, is
> the open fix.

Retraining the gesture models additionally needs `requirements-ml.txt`. An
Intel RealSense camera needs `pip install pyrealsense2`; it is deliberately
not a core dependency, so a webcam-only setup does not pay for it.

Place your hand in the green square, press `z` to calibrate to your skin tone, then outstretch your hand to be detected. Move your hand to move the cursor. `o` toggles out-of-range, `d` starts/stops dragging, `s` single-clicks. Edit `config.yaml` to select the segmentation and control strategy. Full detail: [`cameramouse/README.md`](cameramouse/README.md).

To run tracking alone:
```bash
cd cameramouse
python3 -m hand_tracking --webcam -src 0   # or: --realsense
```

### MediaPipe pipeline (Linux)

Requires MediaPipe v0.7.0 with Bazel v1.2.1. Follow [`mediapipe/README.md`](mediapipe/README.md), then:

```bash
cd mediapipe
./scripts/build.sh
./scripts/run_demo1.sh    # gesture-driven cursor control
./scripts/run_demo2.sh    # MediaPipe + OpenCV segmentation fusion (experimental)
```

**Demo 1** runs the frame-reduced graph. `gesture_detection_calculator.cc` reads the 21 landmarks and emits a gesture ID; `pipe_writing_calculator.cc` computes the centroid of five selected landmarks and writes it with the gesture to a FIFO, consumed by [`mouse_control_for_demo1_with_new_gesures.py`](mouse-control-test/mouse_control_for_demo1_with_new_gesures.py).

> The build currently produces the *old* gesture calculator. To use the newer geometry-based gesture set ([definition slides](https://docs.google.com/presentation/d/1R5K-rlorkxrP03RoG5ys7vCLMY0H_5_y4Tqb3lC5Uv8/edit?usp=sharing)), substitute `gesture_detection_new_calculator.cc` before building. The mouse control script targets the new version.

**Demo 2** fuses HSV colour segmentation with MediaPipe so skin-tone calibration happens automatically on hand detection. It is experimental: MediaPipe false positives and frame-rate mismatch between the two nodes still cause instability. Documented as open work, not as a finished feature.

---

## Open integration interface

The hand stream is deliberately exposed over standard IPC so third-party software can consume it without depending on this project's code.

**Protocol:** UDP · **Address:** `127.0.0.1` · **Ports:** `2000`, `3000`, `4000`

| Port | Payload | Format |
| --- | --- | --- |
| `2000`, `3000` | 21 hand landmarks | `"x_i, y_i, z_i;"` for `1 <= i <= 21`, each a float in `[0, 1]` |
| `4000` | Hand centroid + bounding box | `"x_cent, y_cent, x_rect, y_rect, w_rect, h_rect;"` (Demo 2 only) |

A named FIFO (`Mouse`, created with `mkfifo Mouse`) carries `x, y, gesture_id` to the cursor controller.

Because the format is plain text over localhost UDP, a downstream consumer can be written in Python, JavaScript, Rust, or C in a few lines — which is the intent. The tracking is the reusable asset; the cursor is only one possible consumer of it.

---

## Datasets released

`gesture_learning/data/` — every line is the `(x, y)` coordinates of 21 landmarks plus a class label, normalised against the palm keypoint.

| File | Samples | Classes |
| --- | --- | --- |
| `twoClass.txt` | 2,686 | close (0), open (1) |
| `threeClass.txt` | 4,036 | close (0), OK (1), open (2) |
| `fourClass.txt` | 5,087 | close (0), open (1), OK (2), click / index bent (3) |
| `fiveClass.txt` | 8,123 | close (0), open (1), scroll_down / index out (2), scroll_up / index+middle out (3), slow / thumb out (4) |
| **Total** | **19,932** | |

`data/groundtruth/` holds four recorded motion videos (small/large × circle/left-right) with the corresponding pipeline output in `data/mediapipe_output/`, forming a regression benchmark for tracking changes. `gesture_learning/keypoints.py` provides the parsing, UDP decoding, and normalisation utilities; `gesture_learning/template.py` is a ready-to-extend training scaffold.

---

## Reproducible evaluation harness

Assistive input devices are judged on whether a real user can hit a real target, not on model accuracy. `testing/` contains three repeatable, quantitative tests:

- **`AccuracyTest.py`** — pointing/tracing accuracy. Renders a target letter, has the user trace it with the cursor, and scores the result by pixel overlap: `50 × (inside / letter) + 50 × (inside / drawn)`, penalising both under-coverage and overshoot. Run as `./AccuracyTest.py HELLO` to score a sequence.
- **`button_click.py`** — click acquisition accuracy against targets.
- **`selection_test.html`** — click-and-drag selection accuracy in a real browser.

These produce comparable numbers across input methods, so "is the camera mouse good enough yet?" is an empirical question rather than an opinion.

---

## Repository map

| Path | Contents |
| --- | --- |
| `cameramouse/` | Cross-platform OpenCV pipeline — tracking, filtering, control, actuation |
| `cameramouse/config.yaml` | Module selection and tunable constants for the whole pipeline |
| `cameramouse/control/filters.py` | IIR/FIR filters for tremor and jitter suppression |
| `cameramouse/control/controllers.py` | Hand-motion → cursor-motion mapping strategies |
| `cameramouse/hand_tracking/` | HSV segmentation and predictive hand tracking |
| `mediapipe/.../util/gesture_detection_calculator.cc` | Geometry-based gesture recognition (original) |
| `mediapipe/.../util/gesture_detection_new_calculator.cc` | Expanded gesture vocabulary via hand geometry |
| `mediapipe/.../util/pipe_writing_calculator.cc` | Centroid computation + FIFO egress |
| `mediapipe/.../util/landmark_forwarder_calculator.cc` | 21-landmark UDP publisher |
| `mediapipe/.../util/hand_tracking_calculator.cc` | OpenCV segmentation fused into the MediaPipe graph |
| `colour_segmentation_cpp/` | C++ port of the OpenCV tracker (build with CMake) |
| `gesture_learning/` | Feature engineering, model training, datasets, notebooks |
| `mouse-control-test/` | Cursor controllers consuming the MediaPipe stream |
| `testing/` | Reproducible accuracy benchmarks |
| `data/` | Ground-truth videos and paired pipeline output |

To inspect the MediaPipe graph visually, paste `mediapipe/mediapipe/graphs/hand_tracking/gesture_recognition.pbtxt` into [viz.mediapipe.dev](https://viz.mediapipe.dev/).

---

## Depth camera support

An Intel RealSense depth camera is supported as an alternative input, adding per-pixel depth for more robust hand/background separation. See [librealsense](https://github.com/IntelRealSense/librealsense) for driver setup and [these research slides](https://docs.google.com/presentation/d/1SyncibUJNlsJfWg0QvKgYm_z7swszJZDxj19tprEECY/edit?usp=sharing) for the evaluation of what depth does and does not buy in this application.

---

## Roadmap — where contributors can help

This is where the project is genuinely open to outside work. Each item is scoped to be picked up independently:

1. **Anti-shake filtering for tremor.** The current IIR/FIR filters use constant scale factors. Filters derived from measured tremor spectra would directly improve usability for users with essential tremor or Parkinson's.
2. **Voice input for mouse actions.** Tracking works well with relative control and IIR filtering; the remaining hard problem is distinguishing *actions* (click, drag) from *motion*. Voice sidesteps gesture ambiguity entirely — [Snowboy](https://snowboy.kitt.ai/) was a promising direction.
3. **Better hand segmentation.** Colour segmentation is sensitive to lighting and degrades at frame edges. Learned segmentation would remove the calibration step.
4. **Cross-platform MediaPipe.** The MediaPipe path is Linux-only today; a Windows/macOS build would unify the two pipelines.
5. **Stabilising Demo 2.** Decoupling node frame rates so the OpenCV segmentation node keeps receiving frames when landmark inference stalls.
6. **OpenCV-only gesture recognition**, to bring the richer gesture vocabulary to the portable pipeline.

Issues and pull requests are welcome. Please open an issue describing the change before large refactors.

---

## Citation

<!-- TODO: replace author list and year with the actual capstone authors and publication year. -->
```bibtex
@software{assistivemousetech,
  title  = {AssistiveMouseTech: Webcam-Only Mouse Control for Users with Motor Impairments},
  author = {TODO: full author list},
  year   = {TODO},
  url    = {https://github.com/ChrisSun99/AssistiveMouseTech}
}
```

---

## Provenance and contributors

<!-- TODO — IMPORTANT: fill this in accurately before submitting this repo as evidence of your own contribution.
     This codebase contains work by multiple people (the cameramouse module and the MediaPipe mouse-control
     scripts carry other authors' names). State plainly which components you authored, which you co-authored,
     and which you integrated. A precise, verifiable attribution is stronger evidence than a vague one. -->

| Component | Contributor(s) |
| --- | --- |
| MediaPipe calculators (gesture detection, pipe writing, landmark forwarding) | _TODO_ |
| Gesture learning, feature engineering, models, datasets | _TODO_ |
| OpenCV `cameramouse` pipeline | _TODO_ |
| C++ colour segmentation port | _TODO_ |
| Evaluation harness | _TODO_ |

Originally developed as an engineering capstone project. The bundled `mediapipe/` directory is a modified fork of [Google MediaPipe](https://github.com/google/mediapipe) v0.7.0; upstream code remains under its original Apache 2.0 licence (`mediapipe/LICENSE`).

## License

<!-- TODO: this repository has no root LICENSE file. Add one (MIT or Apache 2.0 are the conventional choices
     for a project like this; Apache 2.0 matches the bundled MediaPipe fork). An open-source exhibit without
     a licence file is not, strictly speaking, open source — this is worth fixing before submission. -->

_TODO: add a root `LICENSE` file._ Bundled MediaPipe sources are Apache 2.0. Several scripts carry MIT headers.
