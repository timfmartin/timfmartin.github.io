---
layout: page
title: Desk camera stand
description: A 3D-printable stand that puts a camera where your head would be, for egocentric hand tracking.
img: assets/img/desk-stand/overview.png
importance: 2
---

EgoHand is trained on head-mounted video, so the camera for [egohand-live]({% link _projects/egohand-live.md %})
should see your hands from behind and above, the way your own eyes do. This stand holds an Intel
RealSense D405 (or a webcam) on a 20 × 20 mm aluminium extrusion clamped to the desk edge: you
sit behind the bar, reach around it, and work on the desk in front of it.

{% include figure.liquid path="assets/img/desk-stand/overview.png" class="img-fluid rounded z-depth-1" zoomable=true alt="CAD render of the stand: a vertical aluminium bar in a foot clamped to the desk, with the camera head near the top tilted down at the desk" caption="The stand: desk foot, 880 mm bar, and the tilting camera head." %}

- **Four printed parts:** a desk foot that clamps to the desk edge, a camera clamp that slides
  onto the bar at any height, a cradle for the D405, and a wing knob for the tilt lock.
- **No play, whatever the printer's tolerance:** each bore has a pad cut free on three sides that
  an M4 screw presses onto the bar's flat face.
- **Adjustable tilt** from −10° to 90°, locked by a wing knob, with a printed scale. The collar
  height and the tilt reading give the camera pose for the simulator.
- **Standard parts:** a 20 × 20 mm B-type extrusion (6 mm slot) and M3/M4/M5 screws.

<div class="row mt-3">
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/desk-stand/camera_head_iso.png" class="img-fluid rounded z-depth-1" zoomable=true alt="CAD render of the camera head at 45 degrees tilt" caption="Camera head at 45° tilt." %}
  </div>
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/desk-stand/desk_foot.png" class="img-fluid rounded z-depth-1" zoomable=true alt="CAD render of the desk foot with the bar socket" caption="Desk foot with the bar socket." %}
  </div>
  <div class="col-sm mt-3 mt-md-0">
    {% include figure.liquid path="assets/img/desk-stand/cam_clamp_section.png" class="img-fluid rounded z-depth-1" zoomable=true alt="Cut-away of the camera clamp showing the pad that locks the bar" caption="Cut-away: the pad that locks the bar." %}
  </div>
</div>

**Files:** FreeCAD source, STEP and STL in
[egohand-live/hardware/d405_desk_mount](https://github.com/timfmartin/egohand-live/tree/main/hardware/d405_desk_mount).
