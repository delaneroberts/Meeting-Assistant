# Transcript Length & Limitations

## File Size Limits

### Audio File Upload
- **Maximum file size**: 25 MB
- **Applies to**: Audio files uploaded via the browser
- **Formats supported**: m4a, mp3, wav, and other audio formats supported by OpenAI Whisper
- **Error handling**: If file exceeds 25 MB, user gets error: "File is too large. Limit is 25 MB."

## Transcript Processing

### OpenAI Whisper (Transcription)
- **No hard length limit** on transcript output
- **Practical limit**: Depends on audio file duration
  - A 25 MB audio file typically contains 30-40+ hours of audio
  - Whisper can transcribe very long audio files, but may take time
- **Output**: Returns the **complete transcript** without truncation
- **Note**: The transcript is not artificially cut short by the API

## Summarization & Translation

### GPT-4o-mini Token Budget

**Summarization Prompt:**
- `max_tokens=900` - Summary generation
- Produces concise meeting notes (typically 200-500 tokens)
- **No truncation** - full summary is returned

**Transcript Translation (if non-English):**
- `max_tokens=4096` - Large buffer for translating entire transcripts
- At 4096 tokens, can handle ~3000 words of transcript
- **Potential issue**: Very long transcripts (>3000 words) may be partially translated
  - Mitigation: The entire transcript is sent to translate; GPT returns what fits in 4096 tokens
  - For very long meetings, the last portion may be truncated

**Action Items Translation (if non-English):**
- `max_tokens=1024` - Adequate for action items
- Typically 5-10 action items translate to <500 tokens
- **No truncation expected** for action items

**Original Summary Translation (if non-English):**
- `max_tokens=2048` - Buffer for summary translation
- Summaries are typically <500 tokens, so no truncation expected

## Summary of Limitations

| Component | Limit | Notes |
|-----------|-------|-------|
| **Audio Upload** | 25 MB | Clear error if exceeded |
| **Transcription** | None | Returns full transcript |
| **Summary** | None | ~900 tokens output max |
| **Action Items** | None | ~10 items typical |
| **Transcript Translation** | 4096 tokens output | ⚠️ Long transcripts (>3000 words) may be truncated |
| **Summary Translation** | 2048 tokens output | Safe for typical summaries |
| **Action Items Translation** | 1024 tokens output | Safe for typical action items |

## Recommendations

### For Long Meetings (>60 minutes)
1. **Expected**: Transcript will be complete from Whisper
2. **Summary**: Will be concise and complete
3. **Translation**: English version is always complete
   - If translating to another language, the transcript may be truncated at 4096 tokens
   - This is typically ~3000 words (usually covers 80-90% of the meeting)

### To Handle Very Long Transcripts Better
Options to consider in the future:
1. **Chunking**: Split very long transcripts into sections before translating
2. **Token counting**: Pre-check transcript length and warn user if translation may be truncated
3. **Summarize first**: Translate the summary instead of the full transcript for very long meetings
4. **Higher token limit**: Request increase from OpenAI (currently using gpt-4o-mini limits)

## Current Behavior

✅ **Working well:**
- Short to medium meetings (up to 60 minutes)
- All transcripts are fully captured
- Translations are complete for typical meetings

⚠️ **Potential issues:**
- Very long meetings (>60 minutes) may have truncated translations
- This only affects non-English meetings when translating to another language
- English versions are always complete

## Testing Notes

To test with long transcripts:
1. Record or upload a meeting >45 minutes long
2. If not in English, try translating to another language
3. Check if all content appears in the translation
4. Full transcript will always be saved to `transcripts/` folder regardless
