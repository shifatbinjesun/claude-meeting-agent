# Languages

Claumeet's voice runs on Gemini Live native-audio models. They detect and speak many languages on their own.
Claumeet adds three settings (Control Center → Personality Studio → Language):

| Setting | Options | Effect |
|---|---|---|
| Claumeet speaks | **Auto** (default) or one of the languages below | Auto replies in the language of the person speaking. A fixed default is used unless someone speaks another language. |
| Style | **Bangladeshi** (default) or **Global** | Bangladeshi adds Dhakaiya/Banglish flavour when speaking Bangla. Global speaks every language in a neutral native style. |
| AI notice languages | English plus any of the languages below | The chat disclosure is posted in these languages, up to the chat length limit. |

Languages with a translated AI notice, welcome and opt-out phrases: English, Bangla, Hindi, Urdu, Arabic, Persian,
Spanish, French, German, Portuguese, Italian, Turkish, Russian, Chinese, Japanese, Korean, Indonesian, Malay,
Vietnamese and Thai.

The English command **"Claumeet stop listening"** always works, in every meeting.

## Honest status
- The development AI wrote these translations. Native speakers haven't reviewed most of them yet. Please send fixes
  (`src/claude_agent/brain/languages.py`, `src/claude_agent/brain/addressing.py`).
- Recognition is tested with unit tests on text. How well Gemini *speaks* each language live hasn't been measured yet.
- Opt-out phrases are tuned to avoid catching plain disagreement ("I disagree", "我不同意"), which never pauses Claumeet.
