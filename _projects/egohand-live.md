---
layout: page
title: egohand-live
description: One camera instead of a VR headset. Real-time hand tracking to teleoperate robot hands in Isaac Sim, on a single laptop.
img: assets/img/egohand-live/pipeline.jpg
importance: 1
---

Teleoperating robot hands in NVIDIA Isaac Lab normally means wearing a hand-tracking headset.
egohand-live replaces it with one desk camera: it runs NVIDIA's EgoHand model live, streams both
hands as the 26 OpenXR hand joints a headset would produce, and drives Sharpa Wave robot hands or a
Franka gripper in Isaac Sim. Tracking and simulation run in real time together on one RTX 3080 Ti
laptop, about 65 ms from camera to robot hand.

{% include video.liquid path="assets/video/egohand-live-demo.mp4" poster="/assets/video/egohand-live-demo-poster.jpg" class="img-fluid rounded z-depth-1" controls=true caption="Camera view, hand tracking, the retargeted robot hands, and Isaac Sim with depth and instance segmentation." %}

- **Live hand tracking:** EgoHand (DINOv3 ViT-H+) wrapped for live use, with a causal left/right
  tracker, fp16 inference with CUDA graphs, and online smoothing. 120 → 58–70 ms per frame on a
  laptop GPU.
- **Calibration in minutes:** lens, camera pose and monocular depth scale from a printed ChArUco
  board.
- **Robots:** Sharpa Wave hands over a desk of SimReady props, the same hands on a Franka FR3 Duo,
  and an Isaac Lab driver for gripper tasks that records demonstrations for robot learning.
- **Next:** an Isaac Teleop plugin so Isaac Lab's hand-driven tasks run unchanged with the camera.
  The hand injection already works with no headset attached.

<div class="row mt-3">
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/egohand-live/fr3_duo.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="Two Sharpa Wave robot hands mounted on a Franka FR3 Duo in Isaac Sim" caption="Sharpa Wave hands on a Franka FR3 Duo." %}
  </div>
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/egohand-live/sim_depth_seg.jpg" class="img-fluid rounded z-depth-1" zoomable=true alt="The same Isaac Sim scene as colour, depth and instance segmentation" caption="Isaac Sim view, depth and instance segmentation." %}
  </div>
</div>

**Read more:** the [technical write-up]({% post_url 2026-11-25-egohand-live %}) on how the model was
made real time, and the [desk stand]({% link _projects/desk-camera-stand.md %}) that holds the camera.

**Code:** [github.com/timfmartin/egohand-live](https://github.com/timfmartin/egohand-live) (Apache-2.0)
