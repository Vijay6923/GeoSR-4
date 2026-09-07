# GeoSR-4 — Decision Log

Har major decision yahan likha jayega, saath mein uske peeche ka reason (why), consider kiye gaye alternatives, aur status. Naya decision aane par purane ko edit mat karo — naya entry add karo (agar koi decision revise/reverse hota hai, to us purane entry ka status update karke, uska reference dete hue naya entry banao).

Format: har entry ke paas ID, date, decision, reasoning, alternatives, status hona chahiye.

---

## D001 — Adopt GeoSR-4 PRD as the baseline plan
**Date:** 2026-09-07
**Decision:** `GeoSR-4-Complete-PRD.md` ko project ka baseline reference maana jayega — problem framing, phased build order (Phase 0–13), aur architecture layers usi se follow honge, jab tak koi decision explicitly usse deviate na kare.
**Reasoning:** PRD correctly identifies ki yeh problem sirf "image sharpen karna" nahi hai — asli challenge hai reconstruction + uncertainty + validation, kyunki kuch fine detail model se inferred hota hai, directly observed nahi. Yeh distinction hi project ka strongest scientific point ban sakta hai. PRD ka progressive build order (Bicubic → EDSR/RCAN → SwinIR → custom GeoSR-4) overengineering se bachata hai aur ek ablation-study story bhi deta hai jo judges ke saamne scientifically defensible hai.
**Alternatives considered:** Directly jump to a complex transformer+diffusion architecture — reject kiya kyunki PRD khud isse "Risk 6: Overengineering" bolta hai, aur hackathon timeline mein yeh risk zyada hai reward se.
**Status:** Accepted.

---

## D002 — Use SEN2NAIP dataset for training/validation, prioritize `cross-sensor` split over `synthetic` shards
**Date:** 2026-09-07/08
**Decision:** Training/validation data ke liye `isp-uv-es/SEN2NAIP` (Hugging Face) dataset use karenge. Pehle sirf `cross-sensor/cross-sensor.zip` (real Sentinel-2 ↔ NAIP pairs) use karenge; `synthetic/synthetic_01.zip`–`synthetic_18.zip` shards ko tab tak nahi chhuenge jab tak pipeline end-to-end kaam nahi kar raha aur genuinely zyada training volume chahiye.
**Reasoning:**
- Cross-sensor split mein exactly PRD ke MVP spec se match karta hai: LR (Sentinel-2) = 10 m, HR (NAIP-derived) = 2.5 m → scale factor 4×, jo PRD ke "<4m" target ko almost exactly satisfy karta hai.
- Bands RGBNIR hain, jo PRD ke MVP band choice (B2/B3/B4/B8) se directly map karte hain.
- Yeh **real** paired data hai (Strategy A, PRD §43), synthetic degradation (Strategy B) nahi — scientifically stronger starting point, PRD ki apni recommendation ke mutabik ("best approach: synthetic pehle, phir real data se validate/fine-tune").
- Cross-sensor pairs ko dataset authors ne <1 day acquisition-gap filter se banaya hai, jo PRD ke apne "Risk 2 — Misalignment" concern ko kaafi had tak address karta hai.
- File size: `cross-sensor.zip` sirf ~2.1 GB hai (confirmed via HF API), jabki poora repo (18 synthetic shards + cross-sensor) ~180 GB ka hai. Poora dataset download karna is stage par unnecessary aur laptop disk/bandwidth ke liye impractical hai.
- License CC-BY-4.0 hai — hackathon use ke liye clean, sirf attribution chahiye.
**Alternatives considered:**
- Poora dataset (180 GB) ek saath download karna — reject kiya: PRD ka apna "Risk 6: Overengineering" isi tarah ke premature scope-creep ko warn karta hai, aur cross-sensor split akela pipeline validate karne ke liye kaafi hai.
- Sirf synthetic shards se start karna — reject kiya: cross-sensor split available hone ke bawajood synthetic-only start karna scientifically weaker hota (real data ki jagah simulated degradation), jabki real data available aur chhota size mein hai.
- India-specific HR source (Cartosat/Bhuvan) dhoondhna — abhi tak koi ready-to-use paired dataset identify nahi hua hai; is decision ko open rakha gaya hai (see "Open Considerations" neeche).
**Status:** Accepted. Cross-sensor pull kiya ja raha hai (D003 dekho).

---

## D003 — Store dataset under `ml/datasets/raw/sen2naip/`
**Date:** 2026-09-08
**Decision:** Downloaded zip aur extracted files `ml/datasets/raw/sen2naip/` ke andar rakhenge, PRD ke repo-structure (`ml/datasets/`) ke mutabik.
**Reasoning:** PRD ka Section 58 repo layout already `ml/datasets/` ko dataset-related cheezon ke liye designate karta hai — koi naya convention banane ki zaroorat nahi.
**Alternatives considered:** Root-level `/data` folder (PRD Section 19 mein prototype storage ke liye suggest kiya gaya) — reject kiya kyunki woh runtime/inference storage (`input/processed/output/uncertainty/models`) ke liye hai, training dataset ke liye nahi. Training data `ml/datasets/` mein rehna zyada consistent hai ML pipeline code ke saath.
**Status:** Accepted.

---

## D004 — Adopt PRD's proposed repo structure as-is for the directory skeleton, defer heavy infra implementation
**Date:** 2026-09-08
**Decision:** PRD Section 58 ka poora directory skeleton (`frontend/`, `backend/`, `ml/`, `geospatial/`, `experiments/`, `notebooks/`, `configs/`, `tests/`, `docker/`) create kar diya gaya hai. Lekin PostGIS/Redis/Celery/S3-MinIO jaisa heavy infra, aur DINOv3 perceptual loss / ensemble-based uncertainty jaisi PRD ki "nice-to-have" choices, **abhi implement nahi ki jayengi** — sirf folder skeleton maujood hai, code nahi.
**Reasoning:** Directory layout khud lightweight hai — empty folders banane mein koi cost nahi, aur future code isi structure mein cleanly fit ho jayega. Lekin actual infra (PostGIS/Redis/Celery) aur exotic loss/uncertainty components ko abhi build karna PRD ke apne "Risk 6: Overengineering" warning ke against jaata — MVP ke liye simpler alternatives (local file storage, synchronous/simple background tasks, single-pass heteroscedastic uncertainty instead of MC ensemble) zyada hackathon-realistic hain. Yeh final nahi hai — jab team infra scaling ki zarurat mehsoos kare, tab yeh decision revisit hoga.
**Alternatives considered:** Poora backend stack (FastAPI+PostGIS+Redis+Celery) turant scaffold karna — abhi ke liye deprioritize kiya, kyunki koi backend code likhne ka explicit ask nahi tha is step mein; sirf structure banane ka tha.
**Status:** Accepted (structure only). Infra/implementation decisions open hain — dekho "Open Considerations".

---

## D005 — Git repo init: exclude raw dataset and future build artifacts via `.gitignore`
**Date:** 2026-09-08
**Decision:** Repo ko `git init` karke `https://github.com/Vijay6923/GeoSR-4.git` par push kiya. `.gitignore` mein `ml/datasets/raw/` (aur generally `*.zip`), Python/Node build artifacts, model checkpoints, `.env`, aur runtime `/data/` dir ko exclude kiya. `README.md` naya banaya (PRD/decisions.md/dataset ka pointer, repo structure overview).
**Reasoning:** `cross-sensor.zip` (2.1 GB) GitHub ki 100 MB per-file hard limit se 20x bada hai — push hoga hi nahi. Aur commit karne ki zarurat bhi nahi kyunki ek `hf_hub_download` call se reproduce ho jata hai (D002 mein documented). Build artifacts (`node_modules`, `__pycache__`, checkpoints) bhi isi tarah reproducible/generated hain, repo mein rakhna sirf bloat karega.
**Alternatives considered:** Git LFS use karke dataset ko track karna — abhi ke liye reject kiya, kyunki dataset already ek documented one-line command se re-fetchable hai; LFS ka setup overhead is stage par unnecessary hai.
**Status:** Accepted.

---

## D006 — Phase 1 close-out: verified dataset structure empirically (not just from the paper)
**Date:** 2026-09-08
**Decision:** `cross-sensor.zip` extract karke actual files inspect kiye, sirf paper ke summary par trust nahi kiya. Verified: 2,851 `ROI_*` folders, har ek mein `lr.tif` (4×121×121, int32, EPSG:32611, 10 m, nodata=-2147483648), `hr.tif` (4×484×484, uint8, 2.5 m, nodata=0), aur `metadata.json` (s2_id, s2_date, naip_id, naip_date, QA1, QA2). 626 distinct MGRS tiles mile (S2 scene id se extract kiya), jo geographic diversity confirm karta hai for a proper region-disjoint split.
**Reasoning:** PRD khud kehta hai "validation against reference data is essential" — wahi principle apne dataset assumptions par bhi apply hona chahiye. Band order (R,G,B,NIR) empirically confirm kiya pixel statistics se (band 3 ka mean sabse zyada — NIR ke liye expected, vegetation ki wajah se). Yeh Phase 1 ("Dataset v1") ka deliverable complete karta hai.
**Alternatives considered:** Paper ke documented specs par blindly trust karke seedha training code likhna — reject kiya, kyunki agar assumptions galat nikalte to baad mein training silently broken hota (wrong band order ya wrong normalization divisor jaisi cheezein debug karna mushkil hai).
**Status:** Accepted. Phase 1 complete.

---

## D007 — Phase 2: tile-disjoint train/val/test split, in-memory Dataset/DataLoader instead of pre-dumped `.npy` patches
**Date:** 2026-09-08
**Decision:** `ml/datasets/sen2naip.py` mein ek `tile_disjoint_split()` function likha jo ROIs ko unke S2 MGRS tile ke hisaab se group karke poore tile ko ek hi split (train/val/test — 80/10/10 by tile count) mein daalta hai, taaki spatially close patches alag-alag splits mein na jaayein. `SEN2NAIPCrossSensor` PyTorch `Dataset` class banayi jo `lr.tif`/`hr.tif` ko rasterio se read karke normalize karti hai (LR ÷10000 reflectance scale, HR ÷255 8-bit scale, dono [0,1] mein clip kiye).

PRD ka Phase 2 deliverable literally `preprocess.py` script tha jo `patch_001.npy` jaisi files disk par dump karta — humne iski jagah direct in-memory `Dataset`/`DataLoader` approach liya.
**Reasoning:**
- Data already pre-patched hai (121×121 / 484×484 fixed-size tiles) — is dataset ke liye separate tiling/patch-extraction step ki zaroorat nahi (woh step Phase 7+ mein relevant hoga jab hum poori Sentinel-2 scene par inference chalayenge, tab tiling zaroori hoga).
- Region-based split PRD ka explicit requirement hai (§45: "never randomly mix neighboring patches... data leakage"). MGRS tile ek natural, metadata mein already available geographic grouping hai — isse manually region-boundary draw karne ki zaroorat nahi padi.
- `.npy` mein pre-dump karna 2,851 pairs ke liye disk space double karta (rasterio read already fast hai prototyping ke liye) — is stage par unnecessary I/O overhead.
- Nodata handling: LR ke nodata pixels (-2147483648) ko 0 se replace kiya normalize karne se pehle, poore ROI ko discard nahi kiya — kyunki edge-of-tile nodata common hai aur pura pair discard karna data loss hoga. Yeh ek simplification hai; agar training mein artifacts dikhein to isko refine karna hoga (see Open Considerations).
**Alternatives considered:** Literal `preprocess.py` → `.npy` files approach — reject kiya (reasoning upar). ROI-level random split (PRD explicitly warns against) — reject kiya.
**Status:** Accepted. Smoke-tested (`ml/datasets/_smoke_test.py`) — batch load, shapes, normalization range, aur tile-disjointness sab verified working.

---

## D008 — Fixed normalization: per-band percentile scaling instead of fixed /10000, /255 divisors
**Date:** 2026-09-08
**Decision:** D007 ka normalization (LR ÷10000, HR ÷255) replace kiya per-band affine scaling se, jahan har band ka [2nd, 98th] percentile TRAIN split ke 300-ROI sample se compute kiya jaata hai (`ml/datasets/compute_stats.py` → `configs/normalization_stats.json`), phir har image ko us range ke hisaab se [0,1] mein clip+scale kiya jaata hai.
**Reasoning:** Bicubic baseline pehli baar run kiya to PSNR sirf 9.83 dB aaya — natural-image SR mein typically bicubic 25-35 dB deta hai, to yeh clearly wrong tha. Diagnosis: LR ka ÷10000 (Sentinel-2 ka theoretical saturation ceiling, jo real scenes shayad hi kabhi touch karte hain) aur HR ka ÷255 (jo already ek separate 8-bit contrast-stretch process — dataset paper confirm karta hai ki `hr.tif` = "NAIPh", NAIP ko S2 ke against histogram-matched, phir 8-bit mein re-quantized) — yeh do completely different, uncalibrated scales hain. Ek hi pair par check kiya: SR (bicubic-upsampled LR) ka std HR ke std se 15-20x chhota tha, jabki correlation moderate-positive tha (0.53-0.63) — matlab spatial alignment thik hai (koi misalignment bug nahi), sirf dono images alag dynamic range use kar rahi thi.

Fix ke baad PSNR 14.07 dB, SSIM 0.38, SAM 17.6°, ERGAS 15.87 (n=279 val pairs) aaya — better, but abhi bhi low-ish compared to typical same-sensor synthetic-degradation SR benchmarks (jahan bicubic often 25+ dB deta hai). Yeh ab genuine hai — cross-sensor real data (S2 vs NAIP, alag spectral response functions, alag viewing/illumination geometry) known-hard hai literature mein, exactly isi wajah se dataset ke authors ne "cross-sensor" (hard, real) aur "synthetic" (easier, same-sensor degradation) splits alag rakhe hain. In numbers ko as-is report kar rahe hain, PRD ke apne "never fabricate metrics" principle ke mutabik.
**Alternatives considered:** Per-image (instead of per-band-global) min-max normalization — reject kiya, kyunki woh scene-to-scene genuine brightness differences ko erase kar deta (jo physically meaningful hai reflectance data ke liye, PRD ke "preserve spectral consistency" requirement ke against jaata). Fixed constants continue karna — reject kiya after diagnosis confirm hua ki woh scientifically invalid comparison de raha tha.
**Status:** Accepted. Real baseline numbers ab pipeline-verified hain, fabricated nahi.

---

## D009 — EDSR baseline: fixed a dead-gradient bug (clamp() inside the training forward pass)
**Date:** 2026-09-08
**Decision:** `EDSR.forward()` se `torch.clamp(output, 0, 1)` hata diya. Model ab raw (unbounded) output deta hai training ke waqt; clamping sirf inference/evaluation wrapper mein apply hoti hai (`train_edsr.py`'s `evaluate()`), final pixel values banane ke liye — model ke andar nahi.
**Reasoning:** 16-block/64-channel EDSR banane se pehle 4-block/16-channel tiny version par overfit sanity check kiya (2 hi training examples par, standard ML debugging practice — agar chhote se model sirf 2 examples bhi overfit nahi kar sakta to pipeline mein zaroor bug hai). Loss 15 epochs (30 steps) tak bilkul flat raha, jo suspicious tha. Gradient norm directly check kiya to woh exactly 0.0 tha step ~50 ke baad — matlab gradient completely mar chuka tha.

Root cause: model ka raw output init ke time already [-0.24, 0.25] range mein tha (kuch pixels 0 se neeche), aur `torch.clamp()` zero-gradient hota hai apni clip range ke bahar. Jaise-jaise training aage badhti, aur zyada pixels [0,1] range ke bahar drift karte gaye (L1 loss ka gradient push karta hai), aur end mein saare outputs saturate ho gaye — ek "dead ReLU"-jaisa trap, lekin poore output tensor ke liye.

Fix ke baad same 2-example overfit test: loss 0.60 → ~0.10 (150 steps mein), gradient norm poore time healthy raha (kabhi 0 nahi hua).
**Alternatives considered:** `sigmoid()` output activation (jo hamesha non-zero gradient deta hai, though extremes par vanishing) — reject kiya kyunki simple linear output + external clamp zyada standard practice hai SR literature mein, aur training ko unnecessarily constrain nahi karta.
**Status:** Accepted. Yeh bug agar catch nahi hota, to Colab/Kaggle par poora real training run silently fail hota (loss kabhi decrease nahi hota) — kaafi compute aur time waste hota debugging mein baad mein.

---

## D010 — Split dev workflow: write/smoke-test code locally (CPU), run real training on Colab (GPU)
**Date:** 2026-09-08
**Decision:** Model/training code is written and validated locally on tiny subsets (few ROIs, few steps, small model config) purely to catch bugs. Actual full training runs (all train-split ROIs, full-size EDSR: 16 blocks/64 channels, many epochs) happen on Colab GPU, via `notebooks/train_edsr_colab.ipynb`, which clones the pushed repo, re-downloads only the cross-sensor split, and reuses the committed `configs/normalization_stats.json` (does not recompute it — must stay identical across local dev and Colab runs).
**Reasoning:** Laptop has no CUDA GPU; a full 2,283-pair EDSR training run would be impractically slow on CPU. But local smoke-testing on tiny subsets before touching Colab compute is what caught the D009 dead-gradient bug in the first place — if that bug had only surfaced on a full Colab GPU run, it would've wasted real Colab compute-time/quota debugging something a 2-example, 30-second local test could catch.
**Alternatives considered:** Train fully on this laptop regardless of speed — rejected by user, given (a) time cost and (b) this exact local-smoke-test-first workflow already proved its value by catching D009.
**Status:** Accepted.

---

## Open Considerations (decided nahi, but track karna hai)

- **Indian HR reference imagery**: Abhi tak koi concrete Indian-AOI paired dataset identify nahi hua. SEN2NAIP US-only (NAIP) hai. Demo ke liye Indian AOI par qualitative (no ground-truth) inference run karna zaroori hoga — isko formal decision banate waqt yahan document karna.
- **Uncertainty estimation method**: PRD MC-ensemble (5x inference) suggest karta hai; single-pass heteroscedastic head (mean+variance in one forward pass) zyada compute-efficient alternative hai. Final choice benchmarking ke baad decide hoga.
- **Backend infra scope for MVP demo**: PostGIS/Redis/Celery vs simpler synchronous/local-storage approach — team ki compute/timeline availability dekh kar decide karna hai.
- **Perceptual loss**: DINOv3 vs standard VGG-based perceptual loss — DINOv3 optional/stretch goal hai per PRD khud bhi.
- **Nodata handling refinement**: Abhi LR nodata pixels ko 0 se replace kiya ja raha hai (D007). Agar training mein edge artifacts dikhein, to proper masking (loss se exclude karna) ya un ROIs ko filter karna consider karna hoga jinme nodata fraction zyada hai.
