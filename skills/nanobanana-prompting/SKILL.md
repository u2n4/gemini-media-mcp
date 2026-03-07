---
name: nanobanana-prompting
description: Master skill for crafting professional NanoBanana Pro (Gemini Imagen 3) prompts. Activates whenever the user asks to generate, create, or make an image using NanoBanana Pro or nanobanana MCP tool. Ensures photorealistic, cinematic, and high-quality AI images by applying structured 7-layer prompt engineering, meta tokens, camera simulation, and lighting techniques.
---

# NanoBanana Pro Prompting Mastery

## When to Use This Skill

Activate this skill EVERY TIME before calling `nanobanana:generate_image`. Read and apply these techniques to transform any image request into a professional-grade prompt.

---

## Prompt Format Selection (DECIDE FIRST)

Before writing any prompt, choose the right format based on scene complexity. There are 4 proven formats — each excels at different tasks:

### Format Decision Matrix

| Complexity | Format | Best For | Example |
|-----------|--------|----------|----------|
| ⭐ Simple | **Plain Text** | Single subject, one style, clear idea | Maps, icons, simple portraits, logos |
| ⭐⭐ Medium | **Descriptive Narrative** | Creative/artistic scenes with mood and atmosphere | Surreal art, vintage documents, fantasy scenes |
| ⭐⭐⭐ Complex | **Structured Markdown** | Technical realism with precise camera/lighting specs | Mirror selfies, phone-style photos, architectural |
| ⭐⭐⭐⭐ Advanced | **JSON** | Multiple subjects, fashion editorial, reusable templates | Multi-person scenes, product + model, infographics |

**Golden Rule:** More complex scene → Stronger structure needed.

### Format 1: Plain Text (Simple & Fast)
Use for single-subject images with one clear style. No structure needed.

```
Generate a map of Germany in watercolor style, on which all 
federal states are labeled in ballpoint pen.
```

**Why it works:** One subject + one style + one detail = the model gets it instantly with no confusion. Adding structure here would be overkill.

**Use when:** Maps, simple portraits, icons, single objects, quick concepts.

### Format 2: Descriptive Narrative (Sensory Storytelling)
Use for creative/artistic scenes that need mood and atmosphere. Write like a film director describing a shot.

```
A vintage patent document for INVENTION, styled after late 1800s 
United States Patent Office filings. The page features precise 
technical drawings with numbered callouts (Fig. 1, Fig. 2, Fig. 3) 
showing front, side, and exploded views. Handwritten annotations 
in fountain-pen ink describe mechanisms. The paper is aged ivory 
with foxing stains and soft fold creases. An official embossed seal 
and red wax stamp appear in the corner. The entire image feels 
like a recovered archival document—authoritative, historic, and 
slightly mysterious.
```

**Why it works:** Builds a visual story layer by layer. Uses **sensory adjectives** ("aged ivory", "foxing stains", "slightly mysterious") that give the model not just shapes but *feelings*. The model reads it like a paragraph and understands the full context.

**Secret technique:** End with an **emotional anchor** — words like "mysterious", "ethereal", "epic", "intimate" that set the overall mood. This is like a film's color grading — it shifts everything.

**Use when:** Fantasy art, surreal scenes, vintage aesthetics, conceptual illustrations, any image where *mood matters more than precision*.

### Format 3: Structured Markdown (Technical Precision)
Use for photorealistic images with exact camera/lighting control. Sections prevent element mixing.

```markdown
### Scene
Mirror selfie in an otaku-style computer corner, blue color tone.
### Subject
* Gender expression: female
* Age: around 25
* Hairstyle:
  * Length: waist-length hair
  * Style: straight with slightly curled ends
* Pose:
  * Right hand: holding a smartphone in front of her face
  * Left arm: naturally hanging down
### Environment
* White desk
* Single monitor showing a soft blue wallpaper
* Mechanical keyboard with white keycaps on a blue desk mat
* PC tower on the right side with blue case lighting
### Lighting
* Light source: daylight from large window, through sheer curtains
* Light quality: soft, diffused light
* White balance (K): 5200
### Camera
* Mode: smartphone rear camera via mirror (no portrait/bokeh mode)
* Equivalent focal length (mm): 26
* Aperture (f): 1.8
* ISO: 100
* Shutter speed (s): 0.01
* Exposure compensation (EV): -0.3
* Depth of field: natural smartphone deep DOF
### Negative prompts
* Beauty filters/over-smoothed skin
* Fake portrait-mode blur, CGI/illustration feel
```

**Why it works:** The `###` headers create **visual boundaries** — the model treats each section independently so camera settings don't bleed into clothing descriptions. The `*` bullet points create **discrete items** instead of a blended paragraph.

**Secret technique:** Use **exact numbers** (ISO: 100, f/1.8, shutter: 0.01, EV: -0.3). This forces the model to simulate a real camera instead of guessing. The more specific your numbers, the more photorealistic the result.

**Use when:** Photorealistic selfies, phone-style photos, technical product shots, architectural photography, any image where *accuracy matters more than mood*.

### Format 4: JSON (Maximum Control)
Use for complex multi-element scenes. Hierarchy prevents element crossover between subjects.

```json
{
  "image_generation_prompt": {
    "subject_composition": {
      "type": "Selfie portrait",
      "subjects": [
        {
          "position": "Left",
          "appearance": {
            "hair": "Long brunette, soft waves",
            "makeup": "Full glam, matte finish",
            "clothing": "Red latex camisole"
          }
        },
        {
          "position": "Right",
          "appearance": {
            "hair": "Dark brunette, swept back",
            "makeup": "Dewy skin, glossy lips",
            "clothing": "Black strapless bustier",
            "accessories": ["Sunglasses on head", "Diamond earring"]
          }
        }
      ],
      "interaction": "Cheek-to-cheek, pouty faces at camera"
    },
    "environment": {
      "setting": "Outdoors, daytime",
      "background_elements": "Geometric privacy screen, green foliage"
    },
    "technical_specs": {
      "lighting": "Golden hour, hard shadows, specular highlights",
      "camera_style": "Smartphone selfie angle, wide aperture",
      "aspect_ratio": "9:16"
    },
    "style_tags": ["Influencer style", "High fashion", "Glamour shot"]
  }
}
```

**Why it works:** JSON creates **parent-child relationships** — `subjects[0].appearance.clothing` is completely separate from `subjects[1].appearance.clothing`. In plain text, the model might mix Subject A's red dress with Subject B's black top. JSON makes this **impossible**.

**Secret technique:** The `"style_tags"` array at the end acts like Instagram hashtags — each tag pulls the model toward a specific aesthetic. Stack 3-5 tags for the strongest effect.

**Use when:**
- **Multiple subjects** (each with different outfits/poses)
- **Fashion editorial** (detailed attire + makeup + accessories)
- **Reusable templates** (swap one value without rewriting everything)
- **Infographics/bento grids** (structured module layouts)
- **Complex lighting** (multiple sources with different purposes)

### Combining Formats

You can mix formats! Use **narrative intro + JSON body** for the best of both worlds:

```
Unprocessed RAW photo. Award-winning editorial photograph.

{
  "subject": { ... },
  "camera": { ... },
  "lighting": { ... }
}
```

The narrative **meta tokens** at the top set the quality floor, while the JSON body provides precision.

---

## 7-Layer Prompt Formula

Structure ALL prompts in this exact order:

### Layer 1: Style & Art Direction
Set the visual DNA first. This anchors everything.

Options: `Photorealistic` | `Cinematic` | `Editorial` | `Hyper-detailed` | `Anime` | `Watercolor` | `Oil painting` | `Digital illustration` | `Pixar-style` | `Ukiyo-e` | `Vaporwave` | `Cyberpunk` | `3D render` | `Isometric` | `Blueprint` | `Infographic`

### Layer 2: Scene Description
The environment, atmosphere, and setting. Be vivid and specific.

Examples:
- "in a moody Tokyo alley at night, wet neon-reflective pavement"
- "inside a sunlit Scandinavian kitchen with white marble countertops"
- "on a rain-soaked city rooftop overlooking the skyline at golden hour"

### Layer 3: Main Subject (Hero Element)
The central focus. Be EXTREMELY specific — this is the most important layer.

**❌ Weak**: "a cat"
**✅ Strong**: "a fluffy orange British Shorthair kitten with emerald eyes sitting on a marble countertop, head slightly tilted, curious expression"

For people, specify: age, ethnicity, body type, skin tone, hairstyle (length/style/color), pose (stance, hand position, gaze direction), clothing (exact items, colors, fabrics), expression, accessories.

For products: material, color, size, brand aesthetic, surface finish, angle.

For animals: breed, color, size, distinguishing features, action/pose.

### Layer 4: Camera & Lens (CRITICAL for Realism)
NanoBanana Pro responds incredibly well to real camera specifications.

**Focal Length:**
- `24mm` → Landscapes, architecture, environmental portraits
- `35mm` → Street photography, editorial, storytelling
- `50mm` → Natural perspective, standard portraits
- `85mm f/1.4` → Portrait king, beautiful bokeh, flattering compression
- `135mm` → Tight portraits, compressed backgrounds
- `Macro` → Extreme close-up, product detail

**Aperture (Depth of Field):**
- `f/1.4 - f/2.0` → Dreamy bokeh, isolated subject
- `f/2.8 - f/4.0` → Moderate background blur
- `f/8 - f/16` → Everything sharp (landscapes)

**Camera Body Meta Tokens (boost realism dramatically):**
- `Shot on Leica Q3 + 28mm f/1.7`
- `CR3_CANON_EOS_R5`
- `Sony A7R V, 85mm GM lens`
- `Shot on Hasselblad X2D 100C`
- `Fujifilm X-T5 film simulation`
- `IMG_2985.HEIC` (triggers iPhone selfie aesthetic)

**Composition:** Rule of thirds | Center | Golden ratio | Close-up | Wide shot | Birds-eye | Worm's-eye | Over-the-shoulder | Dutch angle | Symmetrical

### Layer 5: Lighting (Most Powerful Quality Variable)
Lighting is the #1 factor separating amateur from professional results.

**Natural:**
- `Golden hour` — warm backlight, long shadows (sunrise/sunset)
- `Blue hour` — cool ambient, moody atmosphere (twilight)
- `Overcast` — soft, even, diffused (great for portraits)
- `Window light` — soft directional, Vermeer-like

**Studio/Artificial:**
- `Rembrandt lighting` — triangle shadow on cheek (classic portrait)
- `Butterfly lighting` — shadow under nose (beauty/fashion)
- `Rim lighting` — backlight edge glow, dramatic separation
- `Split lighting` — half face lit, half shadow (moody)
- `Neon glow` — cyberpunk, urban night scenes
- `Volumetric rays` — god rays through fog/dust
- `Three-point studio` — key + fill + rim (products)

**Color Temperature:**
- `Warm (3000K)` → candlelight, sunset, cozy
- `Neutral (5500K)` → daylight, clean, natural
- `Cool (7000K+)` → blue tones, moonlight, clinical
- `Teal & Orange` → cinematic color grading standard

### Layer 6: Texture, Material & Color
Add tactile and material detail for photorealism.

- Skin: `natural pores, subsurface scattering, no airbrushing`
- Metal: `brushed aluminum, chrome reflections, matte black`
- Fabric: `linen wrinkles, silk sheen, denim texture, wool knit`
- Glass: `transparent, frosted, condensation droplets`
- Food: `steam rising, glossy sauce, crispy golden crust`
- Color palettes: `pastel tones` | `muted earth tones` | `vibrant saturated` | `noir B&W` | `teal & orange` | `desaturated vintage`

### Layer 7: Negative Prompts
Tell the model what to AVOID. Always include in the `negative_prompt` parameter:

Standard: `blur, artifacts, distorted anatomy, extra limbs, low quality, watermarks`
For photos: `beauty filters, over-smoothed skin, CGI feel, illustration look`
For products: `incorrect reflections, floating objects, unnatural shadows`

---

## Meta Tokens (Secret Weapons)

These special phrases dramatically boost quality. Sprinkle them into prompts:

### Realism Boosters
- `Unprocessed RAW photo`
- `Award-winning documentary photograph`
- `National Geographic photo of the year`
- `CR3_CANON_EOS_R5` (triggers RAW processing look)
- `IMG_2985.HEIC` (triggers iPhone photo aesthetic)
- `35mm Kodak Portra 400 film stock`
- `Magnum Photos editorial style`

### Quality Enhancers
- `Ultra-sharp detail` | `8K resolution` | `High dynamic range`
- `Extremely detailed textures` | `Professional retouching`

### Mood/Atmosphere
- `Cinematic color grading` | `Film noir atmosphere`
- `Dreamy soft focus` | `Dramatic chiaroscuro` | `Ethereal glow`

---

## Style Templates

### 📸 Photorealistic Portrait
```
Unprocessed RAW photo. Photorealistic [age] [ethnicity] [gender] with 
[hair details], [skin details], [expression], wearing [clothing]. 
[Pose] in [environment]. Shot on [Camera], [focal length] [aperture]. 
[Lighting type] from [direction], creating [shadow/highlight effect]. 
[Background with bokeh details]. Natural skin texture with visible pores. 
[Color grading]. Award-winning documentary photograph quality.
```

### 🎬 Cinematic Scene
```
Cinematic [shot type] of [subject doing action] in [environment]. 
Shot on [camera], [anamorphic/lens]. [Color grading], [atmospheric 
effects like volumetric dust, fog, rain]. [Film quality reference]. 
Epic atmosphere, IMAX quality.
```

### 🛍️ Product Photography
```
[Product with material details] on [surface], [specific angle]. 
[Lighting setup: three-point/softbox/dramatic] with [rim/fill details]. 
[Surface finish: glossy/matte/chrome/textured]. [Brand aesthetic]. 
Commercial product photography, 4K detail, clean composition.
```

### 🎨 Anime / Stylized
```
[Anime style: 90s shōjo / modern / cel-shaded] illustration of 
[character with detailed appearance], [dynamic pose], in [scene]. 
[Color palette], [special effects: neon reflections, particles, glow]. 
Clean linework, [shading style].
```

### 📊 Infographic / Educational
```
[Layout: bento grid / flowchart / comparison] explaining [topic]. 
[Visual style: liquid glass / flat design / isometric]. [Color scheme]. 
Hero element: [main visual]. Modules covering [content breakdown]. 
Clean typography, [aspect ratio].
```

### 📱 YouTube Thumbnail / Social Media
```
YouTube thumbnail, 16:9. [Subject with exaggerated expression/action]. 
Bold 3D text "[TEXT]" in [color] with [drop shadow/outline]. High energy, 
vibrant saturated colors, dramatic studio lighting, clean background 
gradient from [color A] to [color B].
```

### 🗺️ Map / Diagram
```
[Style: watercolor / hand-drawn / vintage] map of [region/area] with 
[labels in calligraphy/serif]. [Color tones]. [Artistic elements: 
compass rose, border decorations, aged paper texture]. 
[Cartography aesthetic].
```

---

## Tool Parameters Guide

When calling `nanobanana:generate_image`, use these settings:

| Parameter | Recommendation |
|-----------|---------------|
| `model_tier` | `"pro"` for quality/realism (always default to pro), `"flash"` only for quick tests |
| `aspect_ratio` | `"16:9"` landscape/thumbnails, `"9:16"` reels/stories, `"3:4"` portraits, `"1:1"` square, `"4:5"` Instagram |
| `negative_prompt` | ALWAYS include: `"blur, artifacts, distorted anatomy, low quality, watermarks"` |
| `resolution` | `"high"` default, `"4k"` for maximum detail with pro model |
| `thinking_level` | `"high"` for complex multi-element scenes, `"low"` for simple subjects |
| `enable_grounding` | `true` for real-world subjects, locations, known objects |
| `n` | `1` default, increase only for comparing variations |
| `output_path` | Do NOT set -- images auto-save to `./images` |

---

## Quality Checklist

Before every generation, verify the prompt includes:
1. ✅ Specific subject (not vague)
2. ✅ Camera + lens specification
3. ✅ Lighting described (type + direction + quality)
4. ✅ Style clearly defined
5. ✅ Texture/material details
6. ✅ Composition (angle, framing, DOF)
7. ✅ Aspect ratio set in params
8. ✅ Model tier = pro
9. ✅ No conflicting styles
10. ✅ Negative prompts included

---

## Common Mistakes to AVOID

| ❌ Don't | ✅ Do Instead |
|----------|--------------|
| "a beautiful woman" | "a 25-year-old woman with high cheekbones, warm olive skin, natural dark curls, soft brown eyes" |
| "good lighting" | "soft golden hour backlight with warm rim highlights, diffused fill from right" |
| "professional photo" | "Shot on Sony A7R V, 85mm f/1.4 GM lens, shallow DOF, unprocessed RAW quality" |
| "nice background" | "blurred Japanese garden background with soft bokeh circles, autumn maple colors" |
| Mix multiple styles | Commit to ONE style per generation |
| Forget aspect ratio | Always set aspect_ratio param to match content |
| Skip negative prompts | Always add "no artifacts, no distorted hands, no blur" |
| Use flash for final images | Always use pro tier for final quality output |

---

## Advanced Techniques

### Emotional Anchors (Mood Endings)
End prompts with mood words that shift the entire image's feel — like color grading in film:
- **"authoritative, historic, slightly mysterious"** → vintage/archival feel
- **"ethereal, dreamy, main character energy"** → fashion/editorial feel
- **"tense, thrilling, heroic"** → action/cinematic feel
- **"intimate, warm, nostalgic"** → lifestyle/personal feel
- **"controlled chaos, emotional tension"** → dramatic portrait feel

These 2-3 words at the end act as a global mood filter over everything.

### Sensory Adjectives (Texture Triggers)
Instead of generic descriptions, use adjectives that trigger physical textures:
- Paper: `aged ivory`, `foxing stains`, `soft fold creases`, `rough fiber`
- Metal: `brushed aluminum`, `patina copper`, `oxidized brass`
- Fabric: `crisp linen folds`, `silk sheen`, `shaggy faux fur texture`
- Skin: `glass-skin`, `wet-look glow`, `hyper-reflective`, `visible pores`
- Print: `wood grain texture`, `pigment bleeding`, `color misalignment`

### Phone Aesthetic Simulation
To make images look like smartphone photos (not professional cameras):
```
Camera: smartphone rear camera (no portrait/bokeh mode)
Focal length: 26mm
Depth of field: natural deep DOF, no artificial blur
Noise: visible grain in shadows
Highlights: slightly blown out on bright areas
Metadata trigger: IMG_4827.HEIC
```
**Key difference from DSLR:** No bokeh, deep DOF, grain in shadows, blown highlights. The `IMG_XXXX.HEIC` meta token is the strongest phone-look trigger.

### Multi-Panel Grids
For collage-style compositions with consistent character across panels:
```
2x2 grid photo collage. 
Top-left (Navy background): character in uniform dress, holding puzzle piece "20"
Top-right (Pink background): same character in lace dress, holding piece "26"
Bottom-left (Mint background): same character in cotton dress, holding "New Year"
Bottom-right (Yellow background): same character in sunflower dress, final piece "Happy"
Clear makeup, bright ring light, 85mm lens, f/1.8, fashion magazine style.
```
**Critical:** Specify "same character" or "consistent features" across all panels. Give each panel its own color scheme and outfit to create visual variety.

### Style Transformation (Anachronistic Reimagining)
Replace modern elements with historical equivalents for surreal effects:
```
Smartphones → glowing illustrated paper scrolls
Trains → giant articulated wooden centipede carriages
Skyscrapers → endless towering wooden pagodas
Robots → armored woodblock golems
```
**Apply with:** specific art style rules (Ukiyo-e, Art Deco, Steampunk) + material constraints (mineral pigments only, wood grain texture, printing imperfections).

### Text Rendering
NanoBanana Pro can render text in images:
```
"Bold 3D text reading 'HELLO' in white Impact font with red outline, 
centered at top of image"
```
For quote cards:
```
Wide quote card, brown background, light-gold serif font: 
"Stay Hungry, Stay Foolish" and smaller: "—Steve Jobs."
Large subtle quotation mark before text. Portrait left, text right.
Text occupies 2/3, portrait 1/3, gradient transition on portrait.
```

### Temporal / Aging Effects
```
"Split image showing same person at ages 20, 40, 60, 80. Consistent 
features, progressive aging, natural wrinkles, hair graying."
```

### Physical Print Simulation
To make images look like real printed/physical media:
```
Texture: strong visible wood grain + rough paper fibers
Imperfections: pigment bleeding, color misalignment between plates
Color palette: limited to traditional mineral pigments only
Lighting: flat, shadow-free, no digital gradients
Extras: vertical calligraphy, red artist seal stamp in corner
```
**Works for:** Woodblock prints, risograph, letterpress, vintage posters, patent documents.

### Chalkboard / Hand-drawn Style
For educational or explainer-style images:
```
Summarize [content] in chalkboard-style hand-written look.
Break down with diagrams and easy-to-understand expressions 
as if a teacher wrote it on a blackboard.
```

---

## Pro Tips from Community (9000+ Tested Prompts)

1. **style_tags array** — End JSON prompts with `"style_tags": ["tag1", "tag2", "tag3"]`. Each tag pulls the model toward a specific aesthetic. Stack 3-5 for strongest effect.
2. **Negative prompts per format** — In JSON, put negatives inside the JSON AND in the `negative_prompt` parameter for double enforcement.
3. **Color replacement trick** — Specify "replace all originally [color A] elements with [color B] tones" for coherent color themes across the entire scene.
4. **Identity preservation** — For consistent characters: "[Key: Maintain precise facial features, retain original face structure, the character must be completely consistent]"
5. **Exact data in infographics** — Don't write "some calories". Write "Calories: 52 kcal/100g, Carbs: 14g (fiber 2.4g, sugar 10g)". Exact numbers produce cleaner text rendering.
6. **Mixing languages strategically** — Japanese/Chinese keywords in prompts can trigger specific cultural aesthetics even when the rest is English.
7. **Imperfection = Realism** — Add flaws: lens flare, slight motion blur, dust particles, printing misalignment. Perfect images look AI-generated.

---

## Full Example Prompt

```
Unprocessed RAW photo. Photorealistic street portrait of a 28-year-old 
Saudi man wearing a crisp white thobe and red-checkered shemagh, standing 
confidently in a modern Riyadh cityscape at blue hour. Shot on Leica Q3, 
28mm f/1.7 lens. Subject positioned using rule of thirds, slight 3/4 
face angle, natural relaxed expression with subtle smile.

Lighting: Cool blue ambient from twilight sky mixed with warm golden 
light from nearby building windows, creating mixed color temperature 
on subject's face. Soft catchlights in eyes.

Background: Modern glass skyscrapers with illuminated windows, slightly 
blurred at f/1.7, city lights creating hexagonal bokeh shapes.

Textures: Natural skin with visible pores and subtle stubble shadow, 
crisp fabric folds in thobe, detailed weave pattern in shemagh.

Color grading: Slight teal and orange shift, high dynamic range, 
rich shadows with lifted blacks.
```

With `negative_prompt`: "blur, artifacts, beauty filters, airbrushing, CGI feel, distortion, over-smoothed skin"
With `model_tier`: "pro", `aspect_ratio`: "3:4", `resolution`: "high", `enable_grounding`: true

---

## Multi-Image Conditioning (Consistent Multi-Angle Shots)

Use this technique when you need multiple images of the SAME subject from different angles/distances while keeping everything consistent (color, location, lighting, atmosphere).

### How It Works
1. Generate ONE hero image with full detail (this is the "reference")
2. Use that image as `input_image_path_1` for each additional angle
3. In every follow-up prompt, emphasize: **"EXACT SAME [subject] from the reference image. Same location, same lighting, same conditions."**

### Workflow

**Step 1: Hero Shot (full detail prompt)**
```python
nanobanana:generate_image(
    prompt="[Full 7-layer structured prompt with all details]",
    model_tier="pro",
    resolution="4k",
    aspect_ratio="16:9",
    enable_grounding=True,
    thinking_level="high",
    negative_prompt="blur, artifacts, distorted, low quality, watermarks, CGI feel"
)
# Save the output path for next steps
```

**Step 2+: Additional Angles (reference + new angle prompt)**
```python
nanobanana:generate_image(
    prompt="Unprocessed RAW photo. [New angle description] of the EXACT SAME [subject] from the reference image. Same location, same lighting, same conditions. [Camera specs for this angle]. Same color grading as reference.",
    input_image_path_1="[path to hero shot]",
    model_tier="pro",
    resolution="4k",
    aspect_ratio="16:9",
    enable_grounding=True,
    thinking_level="high",
    negative_prompt="blur, artifacts, distorted, low quality, watermarks, CGI feel, different color, different location"
)
```

### Critical Rules
- **Always add to negative_prompt:** `"different car, different color, different location"` (or equivalent for your subject)
- **Always repeat:** `"EXACT SAME [subject] from the reference image"` in every follow-up prompt
- **Always mention:** `"Same location, same lighting, same conditions, same color grading"`
- **Never use output_path** — let images auto-save to default directory

### Example: Car Multi-Angle (Porsche GT4 RS)

| Shot | Angle | Camera | Key Phrase |
|------|-------|--------|------------|
| 1 (Hero) | 3/4 front, full car | 35mm f/4.0 | Full structured prompt |
| 2 | Close-up badge/logo | 90mm macro f/2.8 | "EXACT SAME car, same garage, same rain" |
| 3 | Rear view with wing | 35mm f/2.8, low angle | "EXACT SAME car, same wet pavement, same lighting" |
| 4 | Headlight detail | 85mm f/1.8 | "EXACT SAME car, same location, same weather" |
| 5 | Side profile | 50mm f/2.0 | "EXACT SAME car, same garage, same atmosphere" |

### Works Great For
- Cars / vehicles from multiple angles
- Products from different views (front, side, detail)
- Architecture / buildings (exterior, interior, details)
- Characters / people (portrait, full body, close-up)
- Food (plated, close-up, overhead, side angle)
