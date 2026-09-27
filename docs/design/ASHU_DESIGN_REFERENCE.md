# Ashu Design Reference Sheet

**Source:** `ashu pics reference.png` (1536×1024, RGB)  
**Location:** `docs/design/ashu_design_reference_sheet.png`  
**Grid:** 4 rows × 6 columns = 24 cells (each ~256×256)

---

## Grid Layout

| Row/Col | 0 | 1 | 2 | 3 | 4 | 5 |
|---------|---|---|---|---|---|---|
| **Row 0** | Neutral/Idle | Neutral variant | Happy/Excited | Happy variant | Excited variant | Excited variant |
| **Row 1** | Curious/Thinking | Curious variant | Surprised/Shocked | Surprised variant | Playful/Teasing | Playful variant |
| **Row 2** | Annoyed/Side-eye | Annoyed variant | Sarcastic/Pout | Caring/Concerned | Caring variant | Proud |
| **Row 3** | Sleepy/Tired | Sleepy variant | Wink/Flirty | Wink variant | Sad/Upset | Sad variant |

---

## Mapping to Asset Manifest (45 Planned Assets)

### Portraits (22 states) — 6 Delivered, 16 Pending

| State | Manifest Status | Grid Reference | Notes |
|-------|----------------|----------------|-------|
| neutral | ✅ Delivered | Row 0, Col 0 | Default idle |
| happy | ✅ Delivered | Row 0, Col 2-3 | Warm positive |
| excited | ✅ Delivered | Row 0, Col 4-5 | High energy |
| curious | ✅ Delivered | Row 1, Col 0-1 | Follow-up prompt |
| surprised | ✅ Delivered | Row 1, Col 2-3 | Shock beat |
| wink | ✅ Delivered | Row 3, Col 2-3 | Affectionate/easter egg |
| laughing | ⏳ Pending | Row 0, Col 4 | Mid-laugh |
| playful | ⏳ Pending | Row 1, Col 4-5 | Cheeky teasing |
| confused | ⏳ Pending | Row 1, Col 0 | Ambiguous input |
| thinking | ⏳ Pending | Row 1, Col 0 | Processing spinner |
| side_eye | ⏳ Pending | Row 2, Col 0-1 | Suspicious/judging |
| pout | ⏳ Pending | Row 2, Col 2 | Mock-offended |
| annoyed | ⏳ Pending | Row 2, Col 0-1 | Mild irritation |
| sarcastic | ⏳ Pending | Row 2, Col 2 | Dry comeback |
| tired | ⏳ Pending | Row 3, Col 0-1 | Late night |
| sleepy | ⏳ Pending | Row 3, Col 0-1 | Bedtime/drowsy |
| concerned | ⏳ Pending | Row 2, Col 3-4 | User distressed |
| caring | ⏳ Pending | Row 2, Col 3-4 | Comforting |
| embarrassed | ⏳ Pending | — | Compliment received |
| proud | ⏳ Pending | Row 2, Col 5 | Achievement |
| teasing | ⏳ Pending | Row 1, Col 4-5 | Flirty provocation |
| sad | ⏳ Pending | Row 3, Col 4-5 | Low mood |

### Voice States (3) — All Pending
| State | Grid Reference |
|-------|----------------|
| listening | Row 1, Col 0 (curious pose) |
| speaking | Row 0, Col 2 (happy pose) |
| reacting | Row 1, Col 2 (surprised pose) |

### Floating Companion (11) — All Pending
| State | Grid Reference |
|-------|----------------|
| float_idle | Row 0, Col 0 |
| float_peeking | Row 1, Col 0 |
| float_sitting | Row 0, Col 0 |
| float_moving | Row 0, Col 4 |
| float_sleeping | Row 3, Col 0 |
| float_happy | Row 0, Col 2 |
| float_excited | Row 0, Col 4 |
| float_annoyed | Row 2, Col 0 |
| float_curious | Row 1, Col 0 |
| float_bored | Row 3, Col 0 |
| float_attention | Row 3, Col 5 |

### Chat Avatars (3) — All Pending
| State | Grid Reference |
|-------|----------------|
| chat_idle | Row 0, Col 0 |
| chat_happy | Row 0, Col 2 |
| chat_annoyed | Row 2, Col 0 |

### Exaggerated Expressions (6) — All Pending
| State | Grid Reference |
|-------|----------------|
| expr_excited | Row 0, Col 4 |
| expr_laughing | Row 0, Col 4 |
| expr_surprised | Row 1, Col 2 |
| expr_annoyed | Row 2, Col 0 |
| expr_sad | Row 3, Col 4 |
| expr_proud | Row 2, Col 5 |

---

## Visual Lock (from Manifest)

- **Hair:** Long wavy slightly-messy dark brown
- **Skin:** Warm light / fair
- **Eyes:** Large expressive dark brown
- **Signature:** Small dainty pink heart-shaped earring
- **Palette:** Peach, cream, soft pink, warm neutral
- **Outfit:** Cropped cream ribbed top with pink bow, oversized cream cardigan, dusty-pink wide-leg cargo pants, cream/white chunky sneakers
- **Style:** Clean modern 2D animation cel, premium animated-series quality, crisp linework, soft cel shading, mild chibi facial exaggeration
- **Never:** Photorealistic, 3D, glossy AI influencer art, overly anime, redesign between assets

---

## Technical Specs (from Manifest)

- **Format:** PNG
- **Color Mode:** RGBA (alpha / transparent background)
- **Canvas:** 2048 × 2048
- **Character Occupancy:** 70-85% of canvas with transparent padding for animation
- **Background:** Fully transparent — no scene, no UI, no text, no speech bubbles
- **Edge Treatment:** Soft chroma key + despill, feathered alpha, clean render edges

---

## Usage Notes

This reference sheet serves as the **visual source of truth** for all 45 planned assets. When new assets are commissioned:

1. Use the corresponding grid cell as the primary pose/expression reference
2. Maintain the visual lock specifications exactly
3. Deliver as 2048×2048 transparent PNG
4. Update the manifest status from `pending_credits` to `delivered`
5. Run the optimization pipeline (crop → 1024px PNG for Android, 512px WebP for web)

The 6 delivered assets (neutral, happy, excited, curious, surprised, wink) have been verified to match their corresponding grid references in the reference sheet.