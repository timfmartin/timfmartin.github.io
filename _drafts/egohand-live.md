---
layout: post
title: "Teleoperating robot hands with one camera: making NVIDIA EgoHand run in real time"
date: 2026-11-25 12:00:00 # TODO(Tim): set the publishing date
description: I replaced the VR headset of Isaac Lab hand teleoperation with one desk camera and NVIDIA's EgoHand model, then made tracking and simulation run in real time together on one laptop.
tags: robotics teleoperation isaac-sim
categories: projects
thumbnail: assets/img/egohand-live/pipeline.jpg
og_image: /assets/img/egohand-live/social_preview.jpg
related_posts: false
toc:
  sidebar: left
---

{% comment %}
Draft for review. Notes for Tim are Liquid comments marked TODO(Tim): they never reach the
rendered page. Run `grep -n "TODO(Tim)" _drafts/egohand-live.md` before publishing.
Every number below is copied from the technical draft.
{% endcomment %}

[egohand-live](https://github.com/timfmartin/egohand-live) lets me teleoperate robot hands in
Isaac Sim with one camera on a desk stand instead of a VR headset. This post is the technical
story behind it: the model, what it took to make it live, the performance work, an honest look at
monocular depth, and the simulator side. All numbers are my own measurements on an RTX 3080 Ti
laptop and, where noted, an RTX 5090.

{% include video.liquid path="assets/video/egohand-live-demo.mp4" poster="/assets/video/egohand-live-demo-poster.jpg" class="img-fluid rounded z-depth-1" controls=true caption="The demo, rendered from a recorded session: the camera view, hand tracking, the robot hands, Isaac Sim, depth and instance segmentation." %}

## TL;DR

- The standard way to teleoperate robot hands in NVIDIA Isaac Lab is a hand-tracking headset
  (Apple Vision Pro or Meta Quest, streamed through CloudXR). I replaced it with **one camera on
  a 3D-printed desk stand** and NVIDIA's **EgoHand** hand-pose model.
- EgoHand ships as an offline video pipeline. Making it live meant a causal hand tracker,
  per-frame batching, online smoothing and a stream of OpenXR hand joints, the format headset
  retargeting already consumes.
- Then the performance work: **120 → 58–70 ms per frame** on a laptop GPU (fp16 with fp16
  accumulation, CUDA graphs, a few surprisingly large inefficiencies), and tuning Isaac Sim's
  renderer so that **tracking and simulation run in real time together on one laptop**,
  ~65 ms from camera to robot hand.
- Monocular depth is the weak spot. Measured against a calibrated desk plane, EgoHand puts
  hands ~10–13 % too close: consistently at ≤ 0.9 m (correctable with one scale factor), and
  randomly beyond ~1 m (not correctable).
- Everything is open source:
  [github.com/timfmartin/egohand-live](https://github.com/timfmartin/egohand-live).

## Why a camera instead of a headset

Hand-tracking headsets are the default input for dexterous teleoperation and for collecting
robot demonstrations: NVIDIA's Isaac Teleop stack streams the headset's 26 OpenXR hand joints
into Isaac Lab, where retargeters turn them into robot hand and arm commands. It works well,
but it means a €330–€4,000 headset, wearing it for every session, and a CloudXR setup.

My question: how far does one ordinary camera get you? Two things made me optimistic:

1. **EgoHand is trained on egocentric video.** A camera placed where your head would be, above
   and behind your hands looking down, sees hands the way the training data did. That is the
   whole idea behind the [desk stand](https://github.com/timfmartin/egohand-live/tree/main/hardware/d405_desk_mount).
2. **The output can be the same as a headset's.** If the camera pipeline produces OpenXR-26
   joints, everything downstream (retargeting, robot control, demo recording) stays NVIDIA's
   standard path.

{% comment %}
TODO(Tim): the left image is the CAD render of the stand from the repo. A photo of the printed
stand on your desk would be better here.
{% endcomment %}

<div class="row mt-3">
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/egohand-live/desk_stand_cad.png" class="img-fluid rounded z-depth-1" zoomable=true alt="CAD render of the desk stand: a vertical aluminium bar clamped to the desk, with the camera near the top looking down at the desk" %}
  </div>
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/egohand-live/camera_view.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="The camera's view: two hands resting on a white desk, seen from behind and above" %}
  </div>
</div>
<div class="caption">
  The desk stand (CAD model, with the camera's field of view in green) and what the camera sees: your hands from behind and above, as a head-mounted camera would.
</div>

## The model: what EgoHand is

[EgoHand](https://github.com/NVIDIA/IsaacCapture/tree/main/src/python/isaaccapture_egopost) comes
from NVIDIA's [Isaac Capture](https://github.com/NVIDIA/IsaacCapture) project (the EgoPost
pipeline). Per image it runs:

| Stage                        | What it does                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| RT-DETR hand detector (ONNX) | boxes and left/right labels at 640 × 640                                              |
| DINOv3 ViT-H+ backbone       | features of a 256 × 256 crop per hand                                                 |
| SOMA hand head               | pose and shape parameters of the SOMA hand model, a camera translation, the hand mesh |

The camera model is perspective (`sam3db_perspective`): it gets the intrinsics, so with correct
calibration the hand comes out in metric camera coordinates. Right hands go through the network
as a mirrored image with a mirrored camera matrix (the model is trained on left hands).

EgoPost is built for whole clips: it tracks hands across the entire video in both directions,
fills gaps, smooths bidirectionally and processes 32-frame batches. None of that works when the
next frame does not exist yet.

## Making it live

**A causal tracker.** Each frame, detections are matched to the previous frame's tracks. Two
lessons from live use:

- _Left/right from position, not from the detector._ With palms facing the camera, the
  detector's left/right class flips (a left palm looks like the back of a right hand). That
  produced mirrored, upside-down hand fits that stuck, because tracking kept the wrong label.
  With the camera behind the operator, the hand further left _is_ the left hand, so the tracker
  assigns sides by image position and swaps tracks when hands cross.
- _A confidence filter against ghost hands._ Desk clutter (a power socket, in my case) was
  detected as a hand with scores of 0.12–0.49. A track is now published only once a running
  average of its detector scores (EMA, α = 0.3) reaches 0.45 over three frames, and dropped
  below 0.25. Real hands survive brief low-score frames; clutter never gets published.

**One frame, both hands, one batch.** Both crops go through the network together.

**A mirror shortcut.** Instead of re-skinning the right hand's mesh after the mirrored pass, I
mirror the output geometrically: identical to the upstream path to < 0.6 mm, and ~20 ms faster
on the 5090.

**Online smoothing.** A [One Euro filter](https://gery.casiez.net/1euro/) on wrist translation
(with a separate, lower cutoff for depth, the noisiest axis) and on hand shape.

**The output.** SOMA's 25 joints are converted to the 26 OpenXR hand joints, with orientations
built from bone directions and the knuckle line (+Y out of the back of the hand, −Z toward the
fingertips), and published as msgpack over ZeroMQ together with the camera pose. Anything can
subscribe: the simulator, a viewer, a retargeting process.

{% include figure.liquid path="assets/img/egohand-live/pipeline.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="Four panels: tracked hands in the camera image, the hand skeletons, the retargeted robot hands, and the robot hands in Isaac Sim" caption="From camera to simulator: the tracked hands in the camera image, the 3D hand joints, the retargeted Sharpa Wave robot hands, and Isaac Sim." %}

More detail on the tracker, the output format and camera setup is in
[docs/tracking.md](https://github.com/timfmartin/egohand-live/blob/main/docs/tracking.md).

## Performance: from 120 to ~60 ms per frame

On the RTX 5090 the first live version ran at ~22 FPS for two hands. On my RTX 3080 Ti laptop,
the machine I wanted it to run on, together with Isaac Sim, it took **~120 ms per frame**.

### Where the time went

I profiled each stage with CUDA synchronisation, two hands:

{% include figure.liquid path="assets/img/egohand-live/stage_latency.svg" class="img-fluid rounded z-depth-1" zoomable=true alt="Bar chart of EgoHand time per frame by stage, baseline vs after: crop preparation 10.2 to 2.1 ms, DINOv3 backbone 56.6 to 26.4 ms, pose head 12.7 to 2.6 ms, SOMA 24.8 to 10.4 ms, rest of the forward pass 11.4 to 7.1 ms" %}

<details markdown="1" class="mb-3">
<summary>The same numbers as a table</summary>

| Stage                      | Baseline |   After |
| -------------------------- | -------: | ------: |
| Crop preparation           |  10.2 ms |  2.1 ms |
| DINOv3 backbone            |  56.6 ms | 26.4 ms |
| Pose head                  |  12.7 ms |  2.6 ms |
| SOMA (shape fit, skinning) |  24.8 ms | 10.4 ms |
| Rest of the forward pass   |  11.4 ms |  7.1 ms |

</details>

The backbone is compute-bound; the head and SOMA are _launch-bound_: many small kernels, each
waiting for Python to issue it. That second category also explained a symptom I had seen: when
other jobs loaded the laptop's CPU, EgoHand slowed from ~95 ms to ~1 s per frame while the GPU
sat idle.

### What helped (cumulative, measured)

| Change                                                | Per&nbsp;frame | Notes                                                                                     |
| ----------------------------------------------------- | -------------: | ----------------------------------------------------------------------------------------- |
| Baseline (bf16)                                       | <span style="white-space: nowrap">118–120 ms</span> |                                                                                           |
| Store backbone weights in the compute dtype           | ~110 ms      | autocast re-cast ~840 M weights, ~5 GB of memory traffic, _every frame_; output identical |
| Stop padding a single hand to a batch of two          |              | one-hand frames 85 → 77 ms predictor time                                                 |
| CUDA graphs, one per hand count                       | 95 ms        | backbone, head and keypoint head replayed as graphs                                       |
| fp16 with fp16 accumulation                           | 86 ms        | see below                                                                                 |
| Precomputed SOMA regressor, GPU crops                 | 72 ms        | SOMA's shape fit 17.7 → 9.1 ms, 25 fewer host syncs                                       |
| Detector through ONNX Runtime IO binding + CUDA graph | 68 ms        | detector 12.4 → 10.2 ms                                                                   |
| Per-block `torch.compile` inside the graphs           | **58–63&nbsp;ms** | ~16 FPS                                                                                   |

GPU memory dropped from 7.6 to 4.6 GB.

**fp16 accumulation was the surprise.** GeForce cards run fp16 matrix multiplies with fp32
accumulation at half the rate of fp16 accumulation (the data-centre parts don't have this
split). PyTorch defaults to fp32 accumulation; `torch.backends.cuda.matmul.allow_fp16_accumulation`
switches it. fp16 with fp32 accumulation gave no gain over bf16; with fp16 accumulation the
backbone got ~10 ms faster. And it was _more_ accurate: against an fp32 reference, fp16 lands at
0.3–0.4 mm mean joint difference, bf16 at 1.3 mm (bf16 has fewer mantissa bits). Peak
activations stayed ~24× below fp16's limit, and a non-finite output would just drop that hand
for a frame.

**A CUDA graph gotcha.** Capturing under `torch.autocast` with its default cast cache made the
graph read freed memory on replay (an illegal memory access). Warm-up and capture need
`torch.autocast(..., cache_enabled=False)`. Also: graph outputs are overwritten by the next
replay of the same shape, so anything that compares against another code path needs graphs off.

**Robustness under CPU load** is the less visible win. With 24 busy processes competing for the
CPU, the worst 1 % of frames went from 725 ms to ~120 ms, because a replayed graph needs one
launch instead of hundreds.

### What didn't help

- **Caching the hand-shape fit** and refitting every N frames saved ~8 ms but moved joints by
  3–7 mm mean (up to 29 mm): the per-frame shape estimate is entangled with the pose.
- **Fewer CPU threads** (`torch` and OpenCV at one thread): no better under load.
- **ONNX Runtime NHWC layout:** slower.
- **Graphing SOMA itself:** not possible without modifying the upstream code (internal
  CPU-to-GPU copies, and warp kernels on their own stream).
- Not tried yet: TensorRT (expected another 5–10 ms), and running the detector only when
  tracking is lost.

## Calibration, and an honest look at monocular depth

### Lens and camera pose

A webcam needs its lens measured once, and every placement needs the camera pose relative to the
desk. Both come from a printed board:

- **Lens:** a ChArUco board (layout and dictionary identified automatically from the first view)
  is detected even when partly outside the image, which matters for covering the corners where
  distortion is largest. Three lens models are fitted (OpenCV standard, rational,
  Kannala-Brandt fisheye) and the best kept. My cheap webcam: 0.14 px reprojection error, 57°
  field of view.
- **Camera pose:** the board lying flat on the desk gives the desk plane by PnP, precise to about
  a millimetre, with no depth estimate involved. My first attempt used hands resting on the desk
  instead, which only works if the monocular depth is already good. It wasn't.

### Measuring the depth error

With the desk plane known, every hand resting flat on the desk has a known true distance along
its viewing ray. That turns depth accuracy into something you can measure in a minute:

| Setup                       | Hand distance | Depth error                       | Correctable?     |
| --------------------------- | ------------- | --------------------------------- | ---------------- |
| Webcam on the wall          | 1.2–1.3 m     | −15 to −24 %, ±12 % between spots | no: random       |
| Webcam on the desk stand    | ~0.9 m        | −13.3 % ± 3.1 %                   | yes: scale 1.15  |
| RealSense D405 on the stand | 0.7–1.0 m     | −10.3 % ± 3.2 %                   | yes: scale 1.11  |

Two takeaways:

1. **EgoHand puts hands consistently too close**, by ~10–13 % in my setups. A single
   `--depth-scale` factor, applied by moving each hand along its viewing ray (so its position in
   the image does not change), fixes that to about ±3 %.
2. **Beyond about 1 m the error becomes random.** At the wall-mounted 1.2 m, the error varied
   ±12 % from one resting spot to the next. Keep the camera within ~0.9 m of the hands, close to
   the head-to-hands distance the model was trained on.

A hypothesis that turned out wrong: I suspected the model's estimate of _hand size_ varied from
pose to pose, which would translate directly into depth error. Recording a minute of tracking
showed the estimated hand length varies by only ~4 %, against 12–15 % depth error. Size explains
at most a third of it.

## Into the simulator

{% comment %}
TODO(Tim): the draft planned a video of the Sharpa hands grasping desk objects here. There is no
such clip yet; the peace-sign still stands in. A short muted loop would fit well (for example
`video.liquid` with autoplay=true loop=true muted=true and a poster).
{% endcomment %}

### Robot hands

Sharpa Wave hands (22 DoF each) in Isaac Lab 3, retargeted with
[dex-retargeting](https://github.com/dexsuite/dex-retargeting)'s DexPilot using the same
configuration and preprocessing as NVIDIA Isaac Teleop's `DexHandRetargeter`. Fingers are
retargeted in the wrist frame, which makes them largely insensitive to the depth error above.

{% include figure.liquid path="assets/img/egohand-live/peace.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="Two Sharpa robot hands making peace signs over a desk of objects in Isaac Sim, with the camera view inset" caption="Peace signs in the camera (inset) and on the Sharpa Wave hands in Isaac Sim." %}

The retargeting optimiser runs in **a separate process**. In a thread inside Kit it took
~300 ms per hand, starved by the GIL; as a child process, 5–15 ms. Later I also had to pin that
process to one BLAS/OpenMP thread: with its default thread pool it fought Kit, PhysX and the
tracker for cores and slowed to 100–200 ms per hand whenever the laptop got busy.

For arms, Franka's official FR3 Duo asset gets a Sharpa hand on each flange, composed in USD into
one articulation, and each tracked wrist drives its arm by damped least-squares IK.

{% include figure.liquid path="assets/img/egohand-live/fr3_duo.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="A Franka FR3 Duo with two arms, each carrying a Sharpa robot hand, over a desk of objects in Isaac Sim" caption="Sharpa Wave hands on Franka's FR3 Duo, composed in USD into one articulation." %}

For parallel grippers, the gripper follows the point between thumb and index fingertip, and a
pinch closes it (below 3 cm; it opens above 5 cm, the rule of Isaac Teleop's gripper
retargeter). That drives Isaac Lab's Franka cube-stacking task and records demonstrations in
Isaac Lab's HDF5 format.

### Making Isaac Sim fast enough to share the GPU

With tracking on the same GPU, every millisecond of rendering is taken from EgoHand. What
mattered, roughly in order:

1. **The renderer.** Isaac Lab cannot choose Kit's render mode, so Isaac Sim starts in RTX
   Real-Time 2.0 with DLSS, which NVIDIA's own performance handbook notes can be slower on
   Ampere GPUs. Switching the viewport to RTX Minimal after start-up took the scene from 0.62×
   to **1.0× real time**, and GPU load from 100 % to ~25 %. For videos I render in full quality
   afterwards (see below).
2. **`sim.step()` renders on every call** unless told otherwise; Isaac Lab's `ManagerBasedRLEnv`
   tasks render `render_interval`-often inside `env.step` (two to three renders per step in the
   stacking task).
3. **CPU PhysX** instead of GPU PhysX for a scene with a few articulations: GPU physics pays a
   GPU-to-Python synchronisation for every state read.
4. **A pacing bug of my own.** My wall-clock pacing reset its schedule whenever a step ran late.
   Render steps always run late, so the cheap physics steps after them waited a full step instead
   of catching up, capping the scene at ~0.75× real time.

And one trap: **Isaac Lab 3 switched quaternions to XYZW.** My gripper teleop assumed WXYZ and
would have pointed the gripper upward.

### End to end, on one laptop

{% comment %}
TODO(Tim): retargeting is "5–15 ms" per hand in the section above (and in the README) but
"4–8 ms per hand" in this table. Both are from the draft; please confirm which applies here, or
say what differs between the two measurements.
{% endcomment %}

|                                              | Measured                                    |
| -------------------------------------------- | ------------------------------------------- |
| Tracking (one hand, webcam)                  | 37–42 ms EgoHand, ~50 ms capture to result  |
| Simulation (Sharpa hands, minimal rendering) | 1.0× real time, ~6 ms per physics step      |
| Retargeting                                  | 4–8 ms per hand                             |
| **Camera to robot hand moving**              | **~65 ms**                                  |

A footnote that cost me an evening: the laptop's firmware occasionally clamps all CPU cores to
400 MHz (zero thermal-throttle events, normal temperatures, original charger), and everything
(tracker, physics, retargeting) slows ~10× at once. `grep MHz /proc/cpuinfo` is now the first
thing I check when the pipeline stutters.

More on the scenes, rigs and options is in
[docs/isaac_sim.md](https://github.com/timfmartin/egohand-live/blob/main/docs/isaac_sim.md).

## Making the video

{% comment %}
TODO(Tim): `--save-session` and `render-video` are in the public repo, but the replay into the
simulator, the Replicator capture and the story-mode renderer are still local-only changes.
Push them before publishing, or add a line saying that part isn't released yet.
{% endcomment %}

The video at the top is rendered offline from a recorded session, not screen-captured:

- `run --save-session` stores every frame the tracker saw with everything computed for it.
- During recording the simulator runs in the light render mode, so tracking stays responsive.
- Afterwards, the recorded hand stream is **replayed into the simulator** in full RTX quality
  (slower than real time, frames tagged with the original camera time), with depth and instance
  segmentation captured through Omniverse Replicator.
- A renderer composes it: wireframe, the robot hand meshes (posed by the same DexPilot
  retargeting, drawn into the camera view from the hand's URDF), the simulator view with the
  camera inset, and wipes into depth and segmentation.

{% include figure.liquid path="assets/img/egohand-live/sim_depth_seg.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="Three views of the same simulated desk scene: the rendered image, a depth map, and an instance segmentation" caption="The replayed session in full RTX quality: the Isaac Sim view, depth and instance segmentation from Omniverse Replicator." %}

## Limitations

- **Monocular depth:** calibrated to a few percent, but estimated, not measured. With a D405,
  fusing its depth sensor would give an absolute wrist distance.
- **A monitor** instead of an immersive view, and no haptics.
- **The viewpoint matters:** the camera has to look over your shoulders.

## What's next

### A drop-in for the headset's hand tracking

Isaac Teleop already lets device plugins replace the headset's hands: NVIDIA's Manus glove
plugin pushes OpenXR hand joints into the CloudXR runtime through a "push device" extension, and
every consumer downstream sees them instead of the headset's. A camera plugin can do the same
with all 26 joints, without any headset or XR client attached. Isaac Lab's hand-driven tasks
(GR1T2 pick-and-place, nut-pour, exhaust-pipe; Unitree G1 with Inspire hands; Galbot stacking)
would then run unchanged on a monitor. Controller-driven tasks would not: the plugin replaces
hand tracking only.

> **Status:** to be confirmed with a spike. Push devices with no headset attached are not
> documented by NVIDIA.
{: .block-warning }

### Data collection for robot learning

The demo recording is there; LeRobot export and GR00T-Mimic augmentation are next.

## Credits

NVIDIA [EgoHand / Isaac Capture](https://github.com/NVIDIA/IsaacCapture) (model and pipeline),
Isaac Sim and Isaac Lab, [dex-retargeting](https://github.com/dexsuite/dex-retargeting),
[Sharpa](https://github.com/sharpa-robotics/sharpa-urdf-usd-xml) (Wave hand models),
[Franka Robotics](https://huggingface.co/datasets/frankarobotics/simready-assets) and
[NVIDIA SimReady](https://huggingface.co/datasets/nvidia/simready-assets) assets.

The code, the desk stand and the docs are on
[GitHub](https://github.com/timfmartin/egohand-live).
