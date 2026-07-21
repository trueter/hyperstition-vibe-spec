# Camera guidance — sub streams via gateway box

Gateway box: `192.168.1.83`, docker `femoid-gateway` (go2rtc).

## Cameras

- **Sentinel** — outdoor
- **Sparkle** — dancefloor

## RTSP restream (VLC: Media → Open Network Stream → paste URI)

```
rtsp://192.168.1.83:8554/sentinel_sub
rtsp://192.168.1.83:8554/sparkle_sub
rtsp://192.168.1.83:8554/sentinel_subweb   # NVENC re-encode, smoother — recommended
rtsp://192.168.1.83:8554/sparkle_subweb    # NVENC re-encode, smoother — recommended
```

### Format

- `_sub` — raw cam, H.264, 1280x720, 20fps (hardware ceiling), 4096kbps CBR, **no audio**
- `_subweb` — NVENC re-encode, H.264, 720p, 20fps, 2Mbps CBR, 1s GOP (steady keyframes, fixes WebRTC freeze on VBR bursts), **no audio**

No audio on either — mic only rides main-stream (`sentinel`/`sparkle`), not sub. Need audio → ask, different stream.

## WHEP/WebRTC (browser)

```
http://192.168.1.83:1984/api/webrtc?src=sentinel_subweb
http://192.168.1.83:1984/api/webrtc?src=sparkle_subweb
```

## go2rtc web UI

Preview, no auth: `http://192.168.1.83:1984`

New display needed → ask first, may need name added to gateway config.
