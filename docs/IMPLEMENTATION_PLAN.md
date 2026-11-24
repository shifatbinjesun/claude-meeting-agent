# Implementation plan

The build follows the release order in the master spec. Each phase ends with something runnable.

1. **Core slice (done in code, tested offline):** config and state machine, policy, owner auth, consent, privacy, memory, Gemini adapters,
   the Meet adapter with the in-page audio bridge, the supervisor gate, emergency stop, and the Windows scripts.
2. **Conversational (implemented, needs live tuning):** persona v1, the turn arbiter (holds while someone speaks, batches greetings,
   handles quiet/serious modes and silence requests), chat replies, reactions, and the owner's private channel.
3. **Second brain (implemented):** FTS5 memory with domains, document ingestion, Wikipedia research, a pronunciation dictionary
   (fed into the prompt), the local approved-meeting scheduler (Asia/Dhaka, Fri/Sat weekend), and items collected while you're away.
4. **Advanced (partial):** vision on demand (off by default; only Claude's own tab), an isolated demo browser (manual share picker).
   Not started: phone access with TLS, Google Calendar OAuth (manual scheduling is used instead).
5. **Hardening (ongoing):** live-meeting trials on your PC, latency measurements, Bangladeshi voice audition with native listeners,
   a long-session soak test, and any fixes those turn up.

## Next steps that need the owner
1. Run `Install-Claude.cmd` on the Windows PC and send back the doctor output.
2. Create and sign in the AI-labeled Google account (`SignIn-Claude.cmd`).
3. Paste a free Gemini key in the Control Center, then run *Probe free models*.
4. Run a private test meeting with you and one consenting person: join, admission, disclosure, a conversation, stop, and leave.
