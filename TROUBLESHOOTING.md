# Meeting Assistant - Troubleshooting Guide

## Problem 1: F12 Key Not Opening Developer Console

**Why it happens:** On macOS, F12 might be mapped to system functions (volume, brightness, etc.) instead of opening developer tools.

**Solutions:**

### Option A: Use Keyboard Shortcut (Recommended)
- **macOS**: Press `Cmd + Option + I` (or `Cmd + Option + J` for Console)
- **Windows/Linux**: Press `Ctrl + Shift + I` (or `Ctrl + Shift + J` for Console)

### Option B: Use Menu
1. **Chrome/Edge**: Click the three-dot menu → **More Tools** → **Developer Tools**
2. **Safari**: 
   - Enable Developer Menu: `Safari` → **Settings** → **Advanced** → Check "Show Develop menu"
   - Then: **Develop** → **Show Web Inspector**

### Option C: Remap F12 on macOS
1. Go to **System Preferences** → **Keyboard** → **Function Keys**
2. Find "Increase/Decrease Brightness" 
3. Remove F12 or remap it to a different key
4. F12 will now open DevTools

---

## Problem 2: "Error: service not allowed" When Clicking Speak

**Why it happens:** The Web Speech API requires:
1. HTTPS (except for localhost)
2. Explicit microphone permission
3. The page must be active in the browser

**Solutions:**

### Step 1: Grant Microphone Permission
1. Open **DevTools** (Cmd+Option+I on Mac)
2. Go to **Console** tab
3. Look for any permission errors
4. Refresh the page
5. When prompted "Allow microphone access?" → Click **Allow**

### Step 2: Check Browser Compatibility
- ✅ **Chrome** - Fully supported
- ✅ **Edge** - Fully supported  
- ✅ **Safari** - Supported (requires permission)
- ❌ **Firefox** - NOT supported (use Chrome instead)
- ❌ **Opera** - Limited support

**If you're using Firefox:** Switch to Chrome or Edge for voice features to work.

### Step 3: Make Sure You're on localhost
- Open your browser's address bar
- Should see: `http://127.0.0.1:8000` or `http://localhost:8000`
- If you're using a different IP address, that may cause permissions issues

### Step 4: Try Again
1. Close the Coach dialog
2. Go back and click the "🎓 Coach" button again
3. Click "Speak Question" tab
4. Click "🎤 Start Speaking"
5. Wait 1 second, then speak clearly

**Debug Tip:** If still getting error, check the Console for the exact error message. Report it along with your browser name/version.

---

## Problem 3: "No transcript available yet" Error

**Why it happens:** You're trying to use Coach before the recording has captured enough audio.

**Solution:**
1. Click **⏺ Record** to start live recording
2. **Speak naturally** for at least 5-10 seconds (so the system captures audio)
3. During or after speaking, click **🎓 Coach** to ask questions
4. Make sure you see the Coach button **enabled** (not grayed out)

**Timing is important:**
- Don't open Coach immediately - let recording run for a few seconds first
- The system needs audio to work with when you ask a question

---

## Problem 4: Auto-detect Questions Not Working

**Why it happens:** Questions may not be detected if:
- Recording hasn't captured enough audio yet
- The detected questions are too similar to mark as "new"
- The GPT API call failed silently

**Solutions:**

### Check the Console for Errors
1. Open DevTools (Cmd+Option+I)
2. Go to **Console** tab
3. Start recording
4. Speak some questions like: "What's the deadline?" or "Who's responsible for this?"
5. Watch for logs like:
   - `"Auto-detect: Processing X chars of new transcript"`
   - `"Auto-detect: Found Y questions"`
   - Any error messages

### Ensure You're Recording Long Enough
- Speak for **at least 15-20 seconds** continuously
- The system detects questions every 8 seconds
- Questions need context to be answered

### If No Questions Appear
Check the Console for:
```
"Auto-detect: Processing 245 chars of new transcript"
"Auto-detect: Found 0 questions"
```

This means the transcript is being captured, but GPT didn't find questions. Try speaking more clearly or asking more obvious questions.

---

## Accessing the Console Tab

### Chrome/Edge/Brave
1. Press **Cmd+Option+I** (Mac) or **Ctrl+Shift+I** (Windows/Linux)
2. Click the **Console** tab at the top
3. You'll see logs like:
   ```
   Live transcription started
   Live transcript updated: 123 chars
   Auto-detect: Processing 245 chars...
   ```

### Safari
1. Press **Cmd+Option+I**
2. Click **Console** tab
3. Same logs as Chrome

---

## Common Error Messages & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Error: service-not-allowed` | Microphone permission denied | Refresh page, allow microphone access |
| `Error: network` | Temporary network issue | Try again, speech recognition will auto-retry |
| `Error: no-speech` | Mic detected but heard silence | Speak louder or check mic volume |
| `Error: audio-capture` | Browser can't access mic | Check system settings, allow access |
| `No transcript available yet` | Recording too short | Let recording run for 5+ seconds first |

---

## Testing Audio Setup

Before using Coach/Auto-detect:

1. **Test your microphone:**
   - Open **System Preferences** → **Sound** → **Input**
   - Speak and watch the input level bars move
   - If no bars move, your mic isn't working

2. **Test in browser:**
   - Go to: https://www.google.com/intl/en/chrome/demos/speech.html
   - Click "Click on the microphone" button
   - Speak a few words
   - If it works here, it works in our app

3. **If not working:**
   - Quit and reopen your browser
   - Check that no other app is using the microphone
   - Restart computer if needed

---

## Need More Help?

1. **Open the Console** (Cmd+Option+I on Mac)
2. **Reproduce the problem** (click Coach, speak, etc.)
3. **Copy all console output** (messages shown in Console tab)
4. **Share that output** - it will help debug the issue

Example log output to look for:
```
Live transcription started
Live transcript updated: 245 chars
Coach voice recognition started
Coach voice recognition ended
Coach transcript: What's the deadline
Coach voice recognition error: no-speech
```
