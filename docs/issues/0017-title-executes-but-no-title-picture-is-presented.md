---
id: 17
title: TITLE executes but no title picture is presented
status: investigating
symptom: after TITLE overlay routing succeeds, headless boot captures only the initial black present and then spends 15-30 seconds in title image-upload/intro-stream GPU/CD work without another presented frame
tags: render,title,overlay,performance,native-producer
created: 2026-08-22
updated: 2026-08-22
---

## Root cause


## What was tried / dead ends


## Resolution

### Note (2026-08-22)
Evidence: scratch/logs/title-overlay-first-run.log reaches ov_title_gen_80071334 and GPU DMA before the 3s watchdog; scratch/logs/title-overlay-watchdog30.log remains inside TITLE while interrupt-time CD/CHD work runs and trips at 30s; scratch/logs/title-overlay-shots.log with watchdog disabled for 15s writes only present_1.ppm, explicitly 0/691200 non-black. The port runs PSXPORT_RENDER_PATH=native but owns zero native producers, so successful guest TITLE execution alone cannot establish a rendered native picture. Do not raise/disable the watchdog as a fix; classify the title intro/image/presenter spine and build the first direct native producer.
