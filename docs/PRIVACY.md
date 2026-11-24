# Privacy, data handling and consent

## What is processed, and where
| Data | Where | Kept? |
|---|---|---|
| Remote meeting audio (after disclosure) | Streamed to the **Google Gemini API** (free tier) for understanding and reply | Not stored locally. Google's terms govern their copies, and free-tier content may be used to improve Google products |
| Transcript lines | In memory (last 300 lines) for the dashboard and context | Cleared when the next meeting starts. Never written to disk by default |
| Meet chat messages | Read in Claumeet's tab. Messages that address Claumeet are sent to Gemini | In memory |
| Questions asked | Local SQLite (question text, asker label) | Until deleted. Revoking a participant deletes theirs |
| Owner notes, approved documents | Local SQLite | Until deleted, or until expiry if a retention period is set |
| Screenshots (vision, off by default) | Claumeet's own Meet tab only, sent once to Gemini | Never stored |
| Gemini API key | Windows Credential Manager | Until you delete it |
| Google sign-in for Claumeet's account | Claumeet's dedicated Chrome profile in `%LOCALAPPDATA%` | Until uninstall |

Deleting local records does not delete copies a provider already received.

## Consent rules built into the code
- No audio, chat or screen processing and no speech before the owner confirms the disclosure. Claumeet also posts the chat disclosure itself.
- Late joiners are flagged "pending" until they receive the greeting and disclosure, and audio processing pauses until then.
- If anyone says or types something like "stop listening", "don't record", "শুনবেন না" or "আমি রাজি না", Claumeet pauses listening right away and confirms in chat.
  Mixed meeting audio can't leave out just one person, so any decline pauses audio processing for everyone.
- Don't use Claumeet for confidential or sensitive meetings while it is on the free tier.

## Disclosure templates (prompts/)
**Bangla:** আসসালামু আলাইকুম সবাইকে! আমি Claumeet, একটা AI সহকারী। {owner} ভাইয়ের অনুমতিতে এই মিটিংয়ে আছি। আমি কথা শুনে উত্তর দিতে পারি, আর আপনাদের কথা প্রসেস করার জন্য Google-এর Gemini সার্ভিসে পাঠানো হয়। কোনো রেকর্ডিং রাখা হয় না। কেউ যদি না চান যে আমি শুনি, শুধু বলবেন বা চ্যাটে লিখবেন, আমি সঙ্গে সঙ্গে শোনা বন্ধ করব।

**English:** Hi everyone! I'm Claumeet, an AI assistant joining with {owner}'s permission. I can listen and reply; what's said here is processed by Google's Gemini service to do that. No recording is kept. If anyone prefers that I don't listen, just say so or type it in chat and I'll stop right away.

**Pre-meeting invite text (copy into your calendar invite):**
> This meeting may include "Claumeet (AI)", an AI assistant. With your consent it listens and replies, and audio is processed by Google Gemini (free tier). No recordings are kept. Tell the host or type "Claumeet stop listening" at any time to pause it.
