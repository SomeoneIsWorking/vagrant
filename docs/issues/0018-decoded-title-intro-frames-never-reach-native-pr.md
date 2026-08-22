---
id: 18
title: Decoded TITLE intro frames never reach native presentation
status: resolved
symptom: TITLE completes MDEC DMA1 callbacks and uploads RGB24 slices to guest VRAM, but the direct-native run presents nothing after the publisher/developer splashes
tags: render,title,mdec,fmv,re-13,native-producer
created: 2026-08-22
updated: 2026-08-22
---

## Root cause

TITLE's guest libpress path successfully streamed, decoded, and uploaded every RGB24 slice into guest
VRAM, but direct-native presentation had no semantic producer for the movie path. The only native
TITLE producer observed the unrelated immediate-sprite splash leaf, so `MovieData::frameComplete`
could become true without any host present request.

## What was tried / dead ends

Treating the 24-bit transition itself as a present trigger was rejected: it describes display mode,
not frame ownership, and would expose incomplete slices. Re-decoding STR data or supplying a canned
frame was also rejected because the intact guest MDEC path already owns those pixels. The measured
completion callback after its generated super-call is the first point at which the final slice is
known to have reached guest VRAM.

## Resolution

### Resolution (2026-08-22)
TITLE's intact libpress/MDEC path already decodes and LoadImage-uploads 24-halfword RGB24 slices into double-buffered guest VRAM, but the direct-native runtime had no semantic owner converting MovieData::frameComplete into a host presentation. VagrantRuntime now retains the callback super-call, latches measured frameComplete, and presents the live guest-selected VRAM scanout at VBlank; it does not read the STR or decode a second frame.
