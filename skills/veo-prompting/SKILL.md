---
name: veo-prompting
description: Master skill for crafting professional VEO 3.1 video prompts. Activates whenever the user asks to generate, create, or make a video using VEO 3.1 MCP tools (veo_generate_video, veo_image_to_video, veo_interpolate_video, veo_extend_video). Ensures cinematic, realistic, and production-grade AI videos by applying structured 7-layer prompt engineering, professional cinematography language, audio design, and lighting techniques. Based on Google's official documentation and 40+ professional sources.
---

# VEO 3.1 Professional Prompting Mastery

## When to Use This Skill

Activate this skill **EVERY TIME** before calling any VEO tool:
- `veo:veo_generate_video` — Text-to-Video
- `veo:veo_image_to_video` — Image-to-Video
- `veo:veo_interpolate_video` — First/Last Frame transitions
- `veo:veo_extend_video` — Extend existing clips

Read and apply these techniques to transform any video request into a cinematic-grade prompt.

---

## Model Capabilities & Constraints

| Parameter | Options |
|-----------|---------|
| **Resolution** | 720p, 1080p (1080p requires 8s duration) |
| **Duration** | 4, 6, or 8 seconds per clip |
| **Aspect Ratio** | 16:9 (landscape), 9:16 (portrait) |
| **Audio** | Native synchronized audio (dialogue, SFX, ambient, music) |
| **Reference Images** | Up to 3 images for character/style consistency |
| **Frame Control** | First frame, last frame, or both for transitions |
| **Extension** | ~7s per extension, max 148s total (720p only) |

### Key Behaviors
- VEO interprets prompts like a **film crew** — precise direction yields precise results
- Front-loaded shot type ensures framing priority
- Without explicit camera direction, defaults to static/subtle handheld
- Audio is generated WITH video — not layered on top
- Same prompt + different seed = very similar output (unlike image models)
- 100-180 words is the sweet spot for text-to-video prompts
- 50-100 words for image-to-video prompts

---

## THE MASTER FORMULA (7 Layers)

```
[1. CINEMATOGRAPHY] + [2. SUBJECT] + [3. ACTION] + [4. ENVIRONMENT] + [5. LIGHTING & MOOD] + [6. AUDIO DESIGN] + [7. TECHNICAL CONTROLS]
```

### Layer 1: CINEMATOGRAPHY (Camera — Always First!)

**Shot Types:** Extreme Wide (EWS) → Wide (WS) → Medium (MS) → Medium Close-Up (MCU) → Close-Up (CU) → Extreme Close-Up (ECU) → Over-the-Shoulder (OTS) → Two-Shot

**Camera Movements:** Static/Tripod | Slow Pan | Dolly In/Out | Tracking | Crane | Aerial/Drone | Handheld | Whip Pan | POV | Orbit/Arc

**Lens & Focus:** 16mm wide-angle | 24mm establishing | 35mm natural | 50mm balanced | 85mm portrait | Macro detail | Shallow DOF f/1.4-2.8 | Deep Focus | Soft Focus

**Angles:** Eye-level (neutral) | Low angle (powerful) | High angle (vulnerable) | Dutch (tension) | Overhead | Worm's eye

> **PRO TIP:** Separate camera movement from subject action in different sentences. "The camera pulls back slowly." as standalone helps VEO parse intent.

### Layer 2: SUBJECT (Lock Identity Early)

**People — 5+ Attributes:** `A [age] [gender] with [hair], [features], wearing [clothing+material], [expression], [posture]`

**Products:** `A [material] [color] [product] with [texture], [features], [size]`

**Material Cues:** "charcoal canvas", "brushed aluminum", "matte ceramic" — gives VEO light-reflection profile that stabilizes subject.

> **PRO TIP:** For multi-shot consistency, copy EXACT same subject description verbatim across all prompts.

### Layer 3: ACTION (Force-Based Verbs)

**❌ Bad:** "walks around", "does something", "moves"
**✅ Good:** "strides confidently", "pushes through the crowd", "lifts the cup slowly"

**Force Verbs:** Push/Pull | Impact (strikes, slams) | Fluid (flows, pours) | Body (breathes, leans) | Subtle (glances, nods)

**Timestamp Beats (8s):** [00:00-02] establishing → [00:02-05] main action → [00:05-08] resolution

> **PRO TIP:** One action per sentence. Never stack competing actions.

### Layer 4: ENVIRONMENT (World as System)

**❌ Flat:** "In a coffee shop"
**✅ Rich:** "Inside a warm cafe at golden hour, soft afternoon light streaming through tall windows, dust particles floating in sunbeams, blurred patrons in background"

**Include:** Time of day + light quality | Weather/particles | Background motion | Depth layers (foreground/mid/background)

### Layer 5: LIGHTING & MOOD

**Always name a physical light source.** Styles: Golden Hour (3200K warm) | Blue Hour (cool twilight) | Rembrandt (45° triangle) | Chiaroscuro (high contrast) | Rim/Backlight (edge glow) | Neon (colored practicals) | Overcast (soft diffused) | Tungsten (warm interior) | Volumetric (rays through haze)

**Formula:** `Key: [source] from [direction]. Fill: [intensity]. Practicals: [visible sources]. Atmosphere: [haze/fog]. Color temp: [K value]`

### Layer 6: AUDIO DESIGN

**Hierarchy:** 1.Dialogue (foreground) → 2.SFX (mid) → 3.Ambient (background) → 4.Music (underscore)

**Format:** `Dialogue: Character says: "Words"` | `SFX: [sound tied to action]` | `Ambient: [2-3 environmental sounds]` | `Music: [genre+instrument+mood], ducked under dialogue`

**Spatial:** "cuts through" (foreground) | "in the distance" (background) | "fills the space" (ambient)

**Tips:** Colon format for speech `says: "words"` | Keep dialogue 3-4 seconds | "no subtitles" always | Audio cues NEAR their action | Max 3-5 ambient elements

### Layer 7: TECHNICAL CONTROLS

**Negative Prompts (always include):** `no text overlays, no watermarks, no subtitles, no captions, no blurry faces, no distorted hands, no unnatural movements, no oversaturation`

**Style Anchors:** Max 1-2. Never mix conflicting styles.

**Film Stocks:** "shot on 35mm" | "8K RED" | "16mm documentary" | "anamorphic widescreen" | "ARRI Alexa"

---

## PROMPT TEMPLATES

### Cinematic Drama
```
Close-up, shallow depth of field, 85mm lens, slow dolly-in. A weathered man in his 60s with deep-set eyes and silver stubble, wearing a faded navy wool coat. He turns slowly toward the window, his jaw tightening as memories surface, fingers gripping the wooden table edge. Dimly lit study at dusk, rain streaming down tall Victorian windows, leather-bound books lining dark shelves, a single desk lamp casting warm amber light. Key: desk lamp warm 2800K. Window providing cool blue fill. Deep shadows in corners. Rain creating moving light patterns on his face. Rain patters heavily against glass. A clock ticks steadily. Distant thunder rolls softly. No music. Cinematic film look, shot on 35mm, slight grain, teal-orange grade. No text overlays, no subtitles. 8 seconds.
```

### Product Reveal
```
Macro to medium, smooth slider left-to-right. A premium matte-black wireless headphone with brushed aluminum accents and soft leather ear cushions. The headphone rotates slowly on a glass surface, light catching each texture detail progressively. Minimalist dark studio, clean negative space. Soft rim light from behind creating edge definition. Key light sweeps slowly from left revealing form and material. SFX: satisfying mechanical click. Soft bass-heavy electronic ambient tone. No dialogue. Ultra-sharp, no fingerprints, no dust, no text overlays. 8 seconds.
```

### Nature/Landscape
```
Wide aerial drone shot, slow push-in descending, 24mm lens, deep focus. A lone hiker with a red backpack at the edge of a massive canyon. The hiker stands motionless gazing as wind gently moves their hair and jacket. Colossal mist-filled canyon at sunrise, jagged formations, morning fog drifting through valleys, golden light painting far walls. Golden hour backlight creating god rays through mist. Volumetric light through atmospheric haze. Wind whistles softly through the canyon. Distant eagle cry echoes. No music. Epic cinematic, shot on RED 8K. No text overlays. 8 seconds, 16:9.
```

### Dialogue Scene
```
Medium close-up, 50mm lens, static tripod at eye level, shallow DOF. A confident woman in her 30s with short black hair, wearing a crisp white linen shirt, warm intelligent eyes. She leans forward making direct eye contact, speaking with calm authority. Modern minimalist office, blurred monitors in background, large windows with city view. Soft window light camera-left at 3/4 angle. She says: "This changes everything we thought we knew." Ambient: quiet office hum, faint air conditioning. No music, no subtitles. 8 seconds.
```

### Food/Culinary
```
Close-up from slightly above, 85mm macro, slow dolly-in, very shallow DOF. A steaming bowl of handmade ramen with rich amber broth, perfectly placed soft-boiled egg, thin noodles, glistening chashu pork. Steam rises gracefully. Chopsticks lift noodles slowly, broth dripping back. Intimate ramen bar, warm wooden counter, paper lanterns above, blurred chef in background. Warm overhead lanterns 3200K, steam catching light beautifully. SFX: soft sizzle, broth simmering, chopsticks on ceramic. No music. Food photography style, warm tones. No text overlays. 8 seconds.
```

### Social Media (9:16)
```
Medium shot, 35mm, slight handheld sway, eye-level front-facing. An energetic fitness trainer in her 20s with high ponytail, bright coral athletic wear, radiant smile. She claps hands excitedly then demonstrates a burpee with explosive energy. Bright outdoor rooftop gym at golden hour, city skyline behind. Golden hour backlight creating hair glow, vibrant warm tones. She says: "Let's get this workout started!" SFX: energetic clap. Upbeat electronic music. No subtitles. 9:16 portrait, 8 seconds.
```

---

## IMAGE-TO-VIDEO (CCAD Framework)

**C**amera + **C**haracter action + **A**udio + **D**etails. Prompts 50-100 words only.

- Do NOT re-describe what the image already shows
- Focus on MOTION — what changes, what moves
- "Maintain the style of the original image"
- Input image = always the starting frame

---

## TIMESTAMP PROMPTING (Multi-Scene)

```
[00:00-00:02] [Camera + Action + Audio]
[00:02-00:04] [Camera + Action + Audio]
[00:04-00:06] [Camera + Action + Audio]
[00:06-00:08] [Camera + Action + Audio]
```

Max 3-4 segments. Keep descriptors consistent across segments.

---

## EXTENSION PROMPTING

"EXTEND: [what happens next]. Maintain same lighting, color palette, camera height."
720p only, ~7s per extension, max 148s total.

---

## FIRST/LAST FRAME PROMPTING

1. Generate Frame A (NanoBanana) → 2. Generate Frame B (NanoBanana) → 3. Describe transition
"The camera performs a smooth [movement] from start to end composition. [Changes]. [Audio]. Seamless motion."

---

## NEGATIVE PROMPT LIBRARY

**Standard:** no text overlays, no watermarks, no subtitles, no captions
**Quality:** no blurry faces, no distorted hands, no extra limbs
**Motion:** no unnatural movements, no jump cuts, no camera shake
**Audio:** no studio audience laughter, no lip-sync issues
**Style:** no oversaturation, no plastic skin, no soap opera effect

---

## 10 GOLDEN RULES

1. **Camera First** — Always start with cinematography
2. **One Action Per Sentence** — Never stack competing actions
3. **Name Your Light Source** — Physical source = stable shadows
4. **Lock Subject Description** — Verbatim across multi-shot
5. **Audio Near Action** — Sound cues next to triggers
6. **100-180 Words** — Sweet spot for text-to-video
7. **3-4 Clips Max** — Timestamp segments to prevent drift
8. **Material Cues** — "wool", "silk", "brushed metal" stabilizes
9. **No Style Collisions** — Max 1-2 anchors per prompt
10. **Always Negative Prompts** — Minimum: "no text overlays, no subtitles"

---

## NanoBanana → VEO Pipeline

**Step 1:** nanobanana:generate_image → hero image
**Step 2:** veo:veo_image_to_video → animate with CCAD prompt
**Step 3:** veo:veo_extend_video → extend if needed (720p)
**Alt:** Generate Frame A + B → veo:veo_interpolate_video

---

## Multi-Clip Video Production (NanoBanana + VEO + FFmpeg)

Use this workflow when the user wants a complete video made of multiple VEO clips merged together with audio.

### Full Pipeline

```
NanoBanana Pro (multi-angle images) → VEO (animate each image) → FFmpeg (trim + merge + audio)
```

### Step 1: Generate Consistent Images
Use NanoBanana's **Multi-Image Conditioning** (see nanobanana-prompting skill):
1. Generate 1 hero image with full detail
2. Use it as `input_image_path_1` for each additional angle
3. Emphasize "EXACT SAME subject" in every prompt

### Step 2: Animate Each Image with VEO
```python
# For each image:
veo:veo_image_to_video(
    image_path="[path to image]",
    prompt="[CCAD: Camera + Character action + Audio + Details]",
    resolution="1080p",  # image-to-video max
    aspect_ratio="16:9",
    model_tier="standard"
)
```
**Tips:**
- Each clip = 8 seconds
- Use CCAD framework (50-100 words, focus on MOTION only)
- Copy subject description verbatim across all prompts

### Step 3: Extract Audio from Original (if remaking a video)
```bash
FF="ffmpeg"
$FF -i "original_video.mp4" -vn -acodec aac -b:a 192k "audio.aac" -y
```

### Step 4: Trim & Merge Clips with FFmpeg

**Calculate clip duration:** `original_audio_duration ÷ number_of_clips`
Example: 22s audio ÷ 5 clips = 4.4s each

**Option A: Clean cuts + fade in/out**
```bash
# Trim each clip to target duration
for i in 1 2 3 4 5; do
  $FF -y -i "clip${i}.mp4" -t 4.4 -an -c:v libx264 -preset fast -crf 18 \
    -pix_fmt yuv420p -r 24 -s 1920x1080 \
    -bsf:v h264_mp4toannexb -f mpegts "clip${i}.ts"
done

# Concat + audio + fade
$FF -y \
  -i "concat:clip1.ts|clip2.ts|clip3.ts|clip4.ts|clip5.ts" \
  -i "audio.aac" \
  -vf "fade=in:st=0:d=0.5,fade=out:st=21:d=1" \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest -movflags +faststart \
  "final_output.mp4"
```

**Option B: Smooth crossfade transitions**
```bash
# Trim clips slightly longer to account for fade overlap
# Formula: (audio_duration + (num_fades × fade_duration)) ÷ num_clips
# Example: (22 + (4 × 0.5)) ÷ 5 = 4.8s each
FADE=0.5

$FF -y \
  -i clip1.ts -i clip2.ts -i clip3.ts -i clip4.ts -i clip5.ts \
  -i audio.aac \
  -filter_complex "
    [0:v]settb=AVTB[v0]; [1:v]settb=AVTB[v1]; [2:v]settb=AVTB[v2];
    [3:v]settb=AVTB[v3]; [4:v]settb=AVTB[v4];
    [v0][v1]xfade=transition=fade:duration=0.5:offset=4.3[x01];
    [x01][v2]xfade=transition=fade:duration=0.5:offset=8.1[x02];
    [x02][v3]xfade=transition=fade:duration=0.5:offset=11.9[x03];
    [x03][v4]xfade=transition=fade:duration=0.5:offset=15.7,
    fade=in:st=0:d=0.5,fade=out:st=17:d=1,format=yuv420p[vout]
  " \
  -map "[vout]" -map 5:a \
  -c:v libx264 -preset slow -crf 16 \
  -c:a aac -b:a 192k -shortest -movflags +faststart \
  "final_crossfade.mp4"
```

### FFmpeg Location
```
ffmpeg
```
Ensure `ffmpeg` is installed and available in your system PATH.

### Quick Reference

| Clips | Audio Duration | Clip Duration (clean) | Clip Duration (crossfade 0.5s) |
|-------|---------------|----------------------|-------------------------------|
| 3 | 15s | 5.0s each | 5.3s each |
| 4 | 20s | 5.0s each | 5.4s each |
| 5 | 22s | 4.4s each | 4.8s each |
| 6 | 30s | 5.0s each | 5.4s each |

**Formula:**
- Clean: `clip_duration = audio_duration ÷ num_clips`
- Crossfade: `clip_duration = (audio_duration + (num_clips - 1) × fade) ÷ num_clips`

### Output
Save final video to: `./videos/`

---

## SOURCES

Built from 40+ sources: Google Cloud Official Guide, Vertex AI Docs, DeepMind, LTX Studio, Leonardo.AI, Replicate, Invideo, DreamHost, GeeLark, Sider.AI, Skywork.AI, Powtoon, Superprompt, snubroot/GitHub, Akool, Vmake, Visla, and community research.
