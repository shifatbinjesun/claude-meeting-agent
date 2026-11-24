# Audio wiring

No virtual audio driver is needed. All meeting audio stays inside Claude's own Chrome tab.

```
                 Claude's dedicated Chrome (Playwright)                       Python supervisor
 ┌─────────────────────────────────────────────────────────────┐   ┌───────────────────────────────┐
 │ Google Meet tab                                             │   │                               │
 │  remote WebRTC audio tracks ──► WebAudio mix ──► 16 kHz PCM ─┼──►│ VAD ─► consent gate ─► Gemini │
 │                                                             │   │                         Live  │
 │  getUserMedia() ◄── WebAudio "mic" ◄── 24 kHz PCM chunks ◄───┼───│ turn arbiter + policy gate ◄──┘
 │  camera request ──► refused (camera always off)             │   │ generation IDs, flush on stop │
 │  physical mic/camera: replaced by Chrome fake devices       │   └───────────────────────────────┘
 └─────────────────────────────────────────────────────────────┘
```

## Scenario A: you and Claude on the same Windows PC
- You join from your normal browser with your own account, mic and speakers. Claude joins from **its own** Chrome window and profile.
- Your microphone goes only into your Meet client. Claude never opens a physical device (fake devices plus the in-page mic).
- Claude hears your voice the same way everyone else does: through Meet's remote audio.
- Claude's Chrome output is muted by Playwright, so Meet audio isn't played twice and you hear Claude only through your own Meet tab.
- Tip: use headphones for your own client, as you would in any meeting, so your speakers don't feed back into your mic.

## Scenario B: you on a phone or another device, Claude on the Windows PC
- Nothing changes on the PC. Claude's tab is fully self-contained.
- Control Claude privately from the Control Center on the PC. Phone access to the dashboard is off by default (see SECURITY.md).

## Why this avoids echo and self-answering
- Meet doesn't send a participant's own audio back to them, so Claude's voice never shows up in Claude's capture.
- No system loopback capture is used, so other apps and private sounds on your PC are never captured.
- Stop, emergency stop and interruptions bump the **generation ID**. `bridge.js` stops every scheduled audio node and refuses any
  late chunk from an old generation. In tests the in-page stop took under 1 ms, and we confirmed silence within 163 ms
  (that time includes the measurement polling).
