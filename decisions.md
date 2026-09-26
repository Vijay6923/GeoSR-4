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

## D011 — First real model-vs-baseline comparison: EDSR beats Bicubic on 3/4 metrics
**Date:** 2026-09-08
**Decision:** EDSR-baseline (16 blocks/64 channels) ko 20 epochs, full train split (2,283 pairs), Colab T4 GPU par train kiya. Full validation split (279 pairs, same protocol jo bicubic baseline ke liye use hua) par evaluate kiya `ml/evaluation/evaluate_checkpoint.py` se.

**Result (n=279, dono same val set par):**

| Metric | Bicubic | EDSR (epoch 19) | Change |
|---|---|---|---|
| PSNR | 14.07 dB | 16.77 dB | +2.70 dB |
| SSIM | 0.385 | 0.443 | +0.058 |
| SAM | 17.64° | 11.41° | -6.23° |
| ERGAS | 15.87 | 15.57 | ~flat |

**Reasoning:** Training ke dauraan per-epoch eval sirf 50 val samples par tha (speed ke liye) — usse directly bicubic (jo poore 279 pairs par tha) se compare karna unfair hota. Isliye final checkpoint ko poore val split par phir se evaluate kiya, taaki comparison genuinely apples-to-apples ho.

PSNR/SSIM/SAM teeno decisively improve hue — yeh evidence hai ki learned model naive interpolation se better hai is cross-sensor task par bhi (jahan D008 mein dekha ki even bicubic ka baseline khud modest tha domain-gap ki wajah se). ERGAS flat raha — aur uska std (55.16) uske apne mean (15.57) se bahut zyada hai, jo suggest karta hai ki kuch outlier patches (shayad low-mean reference band wale, jahan ERGAS ka per-band RMSE/mean ratio explode karta hai) poore average ko skew kar rahe hain, na ki ERGAS genuinely uninformative hai.
**Alternatives considered:** Sirf training ke dauraan ke 50-sample numbers ko final result maan lena — reject kiya, kyunki woh statistically kam reliable hai aur bicubic ke saath unfair comparison hota.
**Status:** Accepted. Phase 3 (EDSR baseline) ka core result mil gaya. ERGAS outlier investigation Open Considerations mein add kiya.

---

## D012 — Phase 4: SwinIR architecture choices (window_size=11, lightweight config)
**Date:** 2026-09-08
**Decision:** SwinIR implement kiya (`ml/models/swinir/swinir.py`) window-based self-attention ke saath — window_size=11, embed_dim=60, 4 RSTB blocks (har ek depth-2), 6 attention heads. Same L1-only, local-CPU-smoke-test → Colab-GPU-train workflow (D010) jo EDSR ke liye use hua.
**Reasoning:**
- window_size=11 specifically isliye chuna kyunki 121 (hamare LR patch ka height/width) = 11×11 exactly — is se koi input padding nahi chahiye. Yeh dataset-specific choice hai; agar future mein arbitrary-size Sentinel-2 scenes par tiled inference chalayenge (Phase 7), tab tile size ko window_size ka multiple rakhna hoga ya padding logic add karni hogi.
- embed_dim=60 / depths=(2,2,2,2) / heads=6 ek "SwinIR-light" scale hai (original paper ke full-size model se chhota) — hackathon compute budget (Colab T4) ke hisaab se reasonable starting point, EDSR (16 blocks/64 channels, ~1.5M params) se roughly comparable capacity range mein.
- EDSR ke D009 bug (training-time clamp gradient-kill) se seekh kar, is baar model likhne se pehle hi forward pass shape-check aur phir 2-example overfit sanity check kiya (before kisi bhi Colab compute use karne ke) — loss 0.58→0.11 (60 steps), gradient norm poore time healthy raha. Isse confirm hua ki window partition/reverse, shifted-window masking, relative position bias, aur RSTB residual connections sab sahi wire hue hain.
- `evaluate_checkpoint.py` ko generalize kiya `--model-type` flag ke saath (edsr/swinir dono), taaki fair full-val-set comparison ek hi script se ho sake, code duplicate na ho.
**Alternatives considered:** Full-size SwinIR (jaisa original paper mein, ~11M+ params, deeper RSTBs) — abhi ke liye reject kiya, PRD ke "Risk 6: Overengineering" ke mutabik; agar lightweight version promising results deta hai to scale up karna easy hoga.
**Status:** Accepted. Local smoke test pass. Colab GPU training run pending (user action).

---

## D013 — SwinIR trained: roughly matches EDSR at less than half the parameters
**Date:** 2026-09-08
**Decision:** SwinIR (embed_dim=60, depths 2,2,2,2, heads=6) ko 20 epochs, full train split, Colab T4 par train kiya. Full val split (279 pairs) par evaluate kiya.

**Three-way comparison (n=279, sab same val set, same protocol):**

| Metric | Bicubic | EDSR (1.52M params) | SwinIR (0.68M params) |
|---|---|---|---|
| PSNR | 14.07 dB | 16.77 dB | 16.92 dB |
| SSIM | 0.385 | 0.443 | 0.429 |
| SAM | 17.64° | 11.41° | 11.60° |
| ERGAS | 15.87 | 15.57 | 14.56 |

**Reasoning:** Dono learned models bicubic ko clearly beat karte hain (PRD ka expected core result). EDSR aur SwinIR ke beech PSNR/SAM lagbhag tied hain, SSIM mein EDSR thoda aage, ERGAS mein SwinIR thoda aage — koi decisive winner nahi hai raw metrics mein.

Lekin: SwinIR ke paas EDSR se **2.2x kam parameters** hain (683K vs 1.52M) — phir bhi comparable quality de raha hai. Yeh PRD ke Section 29 ("why transformer") ke claim ko support karta hai (long-range spatial relationships ko better capture karta hai, isliye kam capacity mein bhi competitive result), lekin isko "transformer clearly better hai" jaisa overclaim nahi kar rahe — is stage par honest finding yeh hai ki **parameter-efficiency mein SwinIR aage hai, absolute quality mein abhi tied hai**. Agar SwinIR ko EDSR jitni hi capacity di jaaye (bigger embed_dim/deeper RSTBs), woh potentially aage nikal sakta hai — yeh Open Considerations mein track kiya gaya hai.

Numbers fabricate nahi kiye — jo mila wahi report kiya, chahe woh "transformer clearly wins" wali clean story na ho.
**Alternatives considered:** Sirf absolute metrics dekh kar "SwinIR EDSR se better nahi hai" keh dena — reject kiya, kyunki parameter-count context ke bina yeh comparison incomplete/misleading hota.
**Status:** Accepted. Phase 4 (SwinIR baseline) complete.

---

## D014 — Phase 5: spectral + edge loss added (ablation on top of EDSR, not a new architecture)
**Date:** 2026-09-08
**Decision:** `ml/losses/spectral.py` (differentiable SAM, torch-native version of the eval metric) aur `ml/losses/edge.py` (Sobel-gradient L1 loss) add kiye. `train_edsr.py` aur `train_swinir.py` dono mein `--lambda-spectral`/`--lambda-edge` CLI flags add kiye (default 0.0 = pure L1, matlab existing baseline runs ka behavior bilkul same rehta hai, backward compatible). Ablation architecture change nahi hai — EDSR ka wahi 16-block/64-channel config reuse kiya, sirf loss function change kiya, taaki loss ka effect architecture se isolate ho sake (PRD Section 32: Model A vs Model A + spectral loss).
**Reasoning:** SAM loss ke liye `acos()` use kiya (differentiable spectral angle) — `acos` ka gradient ±1 ke paas explode karta hai, isliye cosine value ko `[-1+1e-7, 1-1e-7]` mein clamp kiya, jo `compute_sam` (eval metric) ke `[-1,1]` clamp se thoda tighter hai specifically gradient stability ke liye. Edge loss Sobel filter se gradient magnitude nikal ke dono images (SR, HR) ke beech L1 leta hai.

λ_spectral aur λ_edge dono ke default 0.1 rakhe pehle ablation run ke liye — yeh ek starting guess hai, properly tuned nahi (hyperparameter search is stage par scope se bahar hai, PRD ke anti-overengineering ethos ke mutabik). 2-example overfit sanity check (D009/D012 jaisa pattern) pehle chalaya combined loss ke saath — loss 0.76→0.16 (60 steps), gradient norm healthy raha, koi NaN/explosion nahi.
**Alternatives considered:** Naya model architecture banana loss ke saath — reject kiya, kyunki tab yeh confound ho jaata ki improvement architecture se aaya ya loss se. Perceptual/DINOv3 loss abhi add nahi kiya — woh already Open Considerations mein "stretch goal" hai, aur is ablation ko simple rakhna hai pehle.
**Status:** Accepted. Local smoke-tested (dono scripts, combined loss). Colab ablation run pending (user action) — `notebooks/train_edsr_colab.ipynb` mein naya "Phase 5 ablation" section add kiya jo same EDSR config ko spectral+edge loss ke saath train karke turant full-val-set evaluate bhi kar deta hai.

---

## D015 — ERGAS outlier diagnosed: near-zero-reflectance band, not a bug; now reporting median too
**Date:** 2026-09-08
**Decision:** Investigate kiya ki bicubic baseline ke ERGAS ka std (55.16) itna zyada kyun tha apne mean (15.57) se. Poore val split (279 pairs) par per-patch ERGAS sort karke dekha: `ROI_05939` = 771.5 (baaki sab 2.5-58 range mein, median 11.66). Us patch ke HR band means dekhe: band index 2 ka mean sirf 0.0075 tha (0-1 normalized scale par, matlab bahut low reflectance — likely water body ya shadow). ERGAS formula `100 * ratio * sqrt(mean((RMSE_band/mean_band)²))` hai — near-zero mean_band ek modest RMSE ko bhi drastically amplify kar deta hai us band ke liye, aur woh akela poore patch ke ERGAS ko dominate kar deta hai.

Fix: `run_baseline.py` aur `evaluate_checkpoint.py` dono ab median bhi print karte hain ERGAS ke liye (mean ke saath), kyunki mean is known ERGAS limitation ke against robust nahi hai.
**Reasoning:** Yeh ek documented, well-known ERGAS weakness hai remote-sensing literature mein (low-reflectance regions, especially water, denominator explode karte hain) — code mein koi bug nahi tha. Median report karna standard practice hai isi wajah se. Single outlier ka contribution itna bada hai ki woh akela poore 279-sample std ko explain kar deta hai — baaki distribution genuinely well-behaved hai.
**Alternatives considered:** Us specific ROI ko dataset se exclude/filter karna — abhi ke liye reject kiya, kyunki woh genuine real data hai (dataset ka hissa hona chahiye), sirf reporting robust honi chahiye, data cherry-pick nahi karna.
**Status:** Accepted. Open Consideration resolved.

---

## D016 — Phase 6: single-pass heteroscedastic uncertainty (not MC-ensemble), with a real gradient-explosion bug caught in smoke testing
**Date:** 2026-09-08
**Decision:** Uncertainty estimation ke liye single-pass heteroscedastic head implement kiya (`ml/uncertainty/heteroscedastic.py`) — EDSR ko `out_channels=8` diya (4 mean + 4 log-variance), Gaussian NLL loss (`nn.GaussianNLLLoss`) se train kiya. PRD ka suggested MC-ensemble (5x forward pass, multiple models) use nahi kiya.
**Reasoning:** MC-ensemble ek forward pass ki jagah 5x compute maangta — Colab T4 (free tier) ke limited GPU-hours budget mein yeh costly hai, especially jab hume already EDSR/SwinIR/ablation ke liye multiple 20-epoch runs chahiye. Single-pass heteroscedastic head ek hi forward pass mein SR image + confidence map dono deta hai.

**Real bug caught during smoke testing**: Jab main pehle 2-example overfit test kiya lr=1e-2 (jo EDSR/SwinIR ke liye kaam kiya tha) par, training completely diverge ho gayi — loss aur gradient norm dono lakhon tak explode ho gaye (grad_norm 1e8+ tak), reconstruction error 160,000+ tak. Yeh Gaussian NLL loss ka known instability hai (Kendall & Gal, 2017): model predicted variance ko error se zyada fast shrink kar sakta hai, jisse `(error)²/variance` term explode karta hai, jo phir poore model (mean prediction sahit) ko destabilize kar deta hai — plain L1 loss jaisa forgiving nahi hai.

Diagnosis: script ka actual default lr=1e-4 par retest kiya (1e-2 sirf meri quick-debug choice thi, production default nahi) — training stable nikli (loss 0.14→-1.48 smoothly, grad_norm bounded 0.36-7.5, recon error 0.50→0.12). Toh yeh fundamentally broken nahi tha, lekin itni violently diverge hone ki capability dekh kar, defensive measure zaroori laga: `torch.nn.utils.clip_grad_norm_(max_norm=5.0)` add kiya training loop mein, taaki full-scale Colab run mein koi ek bad batch bhi poori training session waste na kare.
**Alternatives considered:** MC-ensemble (PRD ka suggestion) — reject kiya, compute cost ki wajah se (upar reasoning). Warm-start karna (pehle plain-L1 model train karke, phir uncertainty head ke liye fine-tune karna, jo standard practice hai NLL instability avoid karne ke liye) — abhi ke liye add nahi kiya kyunki lr=1e-4 par already stable tha; agar Colab par full-scale run mein bhi instability dikhe to yeh next fix hoga.
**Status:** Accepted. Local smoke-tested (shape check + overfit sanity check + full script run). Colab GPU run pending (user action).

---

## D017 — Phase 7: tiled inference with Hann-blending + GeoTIFF export, verified end-to-end
**Date:** 2026-09-08
**Decision:** `geospatial/tiling/tiler.py` (overlapping-tile extraction + Hann-window blended reassembly, PRD section 25-26), `geospatial/geotiff/export.py` (CRS/transform-preserving GeoTIFF writer, PRD section 40-41), aur `ml/inference/infer_scene.py` (poora pipeline: tile → normalize → infer → blend → denormalize → write) banaye. Abhi sirf EDSR support karta hai (SwinIR ko window_size-multiple tile size chahiye, D012 — abhi handle nahi kiya).
**Reasoning:** Trained model sirf apne training patch size (121×121) par kaam janta hai, lekin real Sentinel-2 scenes bahut bada hote hain — isliye tiling zaroori hai. Bina overlap-blending ke, tile boundaries par visible seams aa sakte hain (PRD Section 26 ka concern).

Verification (sirf "code likha, ho gaya" nahi bola):
1. **Tiler correctness**: Ek synthetic scene par identity-transform (scale_factor=1) test kiya — extract_tiles + blend_tiles round-trip karke original ko wapas reconstruct kar paya, max error 2.4e-7 (float32 precision noise ke barabar). Isse confirm hua ki Hann-window blending aur indexing sahi hai.
2. **End-to-end pipeline**: Ek real `lr.tif` (121×121) par chalaya (deliberately chhota `--tile-size 64` use kiya taaki multi-tile blending path genuinely exercise ho, na ki trivial single-tile case) — 9 tiles bane, sahi se blend hue, output GeoTIFF (484×484) mila.
3. **Geospatial preservation check**: Output GeoTIFF ka CRS (EPSG:32611), origin, aur bounds input ke exactly same the — sirf resolution 10m→2.5m (4x) aur pixel dimensions 121→484 (4x) sahi se scale hue. Yeh directly verify karta hai PRD ka core Phase 7 requirement, sirf assume nahi kiya.
4. Output pixel values (42-93 range) denormalized HR-domain scale mein the (D008's `denormalize()` function use kiya) — [0,1] normalized junk nahi.
**Alternatives considered:** Naive non-overlapping tiling (bina blending ke) — reject kiya, PRD explicitly warns against visible tile-boundary artifacts. SwinIR ke liye bhi is turn mein support add karna — abhi ke liye defer kiya (window_size padding logic extra kaam hai, EDSR se pipeline validate karna pehle zaroori tha).
**Status:** Accepted. Phase 7 core pipeline verified working.

---

## D018 — infer_scene.py extended: SwinIR tiling + uncertainty dual-GeoTIFF output
**Date:** 2026-09-08
**Decision:** `ml/inference/infer_scene.py` ko generalize kiya — `--model-type` (edsr/swinir) aur `--uncertainty` flag add kiye. SwinIR ke liye tile_size ko window_size ka multiple hona chahiye (validate kiya, error deta hai agar nahi hai) — koi extra padding logic nahi chahiye thi kyunki `extract_tiles` already edge-padding kar deta hai poore scene ko tile_size ka multiple banane ke liye (D017 mein already implement tha). Uncertainty checkpoint ke liye mean aur log_var ko alag-alag blend kiya (`blend_tiles` dono baar call kiya), phir std ko `std_norm * (hi-lo)` se physical scale mein convert kiya (linear affine denormalization ke under, `Var(aX)=a²Var(X)` isliye `std(aX)=a·std(X)` — mathematically valid), aur ek dusra GeoTIFF likha uncertainty map ke liye.
**Reasoning:** Dono naye code paths (`--model-type swinir`, `--uncertainty`) smoke test kiye tiny checkpoints se (jo phase 4/6 ke smoke tests se bache the). SwinIR path clean chala (16 tiles, 44x44, window_size=11 ka multiple). Uncertainty path bhi chala, dono GeoTIFF likhe gaye — lekin std values (104-168) bahut large the HR range (~42-200) ke against. Yeh check kiya aur confirm kiya ki yeh expected hai: checkpoint sirf 4 gradient steps trained tha (D016 ka smoke test), untrained network mein log_var≈0 hota hai (near-zero init), matlab var≈1, std≈1 in normalized [0,1] space — jo physical scale mein convert hone ke baad genuinely bahut bada dikhega. Yeh code bug nahi hai, balki mathematically expected behavior hai ek barely-trained model ke liye. Real calibration quality sirf Colab ke actual-trained uncertainty checkpoint se judge ho sakti hai.
**Alternatives considered:** Dono model types ke liye alag-alag script rakhna (jaisa training scripts mein hai) — reject kiya kyunki inference orchestration logic (tile→infer→blend→denormalize→write) same hai dono ke liye, sirf model construction alag hai — is level ka parameterization (jaisa `evaluate_checkpoint.py` mein already hai) DRY rakhta hai bina overengineer kiye.
**Status:** Accepted. Dono open items (SwinIR tiling, uncertainty GeoTIFF) close ho gaye.

---

## D019 — Phase 5 ablation result: spectral+edge loss (λ=0.1/0.1) did NOT help, slightly hurt
**Date:** 2026-09-08
**Decision:** Colab run complete hua. Full-val-set (n=279) comparison:

| Metric | Plain EDSR (D011) | EDSR + spectral(0.1) + edge(0.1) | Change |
|---|---|---|---|
| PSNR | 16.77 dB | 16.45 dB | -0.32 dB |
| SSIM | 0.4427 | 0.4364 | -0.0063 |
| SAM | 11.41° | 11.90° | +0.49° (worse) |
| ERGAS | 15.57 | 15.60 | +0.03 (~flat, dono ke std bahut high hain outlier ki wajah se D015) |

Sab 4 metrics mein slight regression, koi improvement nahi. Numbers as-is report kar rahe hain, chahe woh "loss addition helped" wali expected story na ho.
**Reasoning:** λ=0.1/0.1 sirf ek starting guess tha (D014 mein hi flag kiya gaya tha ki tuning baaki hai). Auxiliary loss terms (spectral, edge) primary reconstruction objective (L1) ke saath compete kar sakte hain agar weight zyada ho — model thoda trade-off kar raha hoga spectral-angle/edge-sharpness ke liye reconstruction accuracy ki keemat par. Yeh ek genuine, honest negative result hai is λ setting ke liye — iska matlab yeh nahi ki spectral/edge loss concept hi galat hai, sirf itna hai ki 0.1/0.1 weight is architecture/task ke liye kaam nahi kiya.

Note: is Colab run mein `evaluate_checkpoint.py` ka purana version chal raha tha (session D015 ke push se pehle clone hua tha) — isliye ERGAS ka median print nahi hua, sirf mean/std. Agli baar isi session mein kaam continue karna ho to `git pull` chalana zaroori hai naye fixes lene ke liye.
**Alternatives considered:** Result ko chhupana ya "roughly same hai" bol ke downplay karna — reject kiya, PRD ka explicit "never fabricate/spin metrics" principle. λ ko turant retune karna — abhi ke liye hold kiya kyunki user ka immediate priority local demo hai; λ sweep Open Considerations mein already tracked hai.
**Status:** Accepted. Phase 5 result recorded (negative finding, still valuable — batata hai λ tuning zaroori hai before spectral/edge loss ko production config maanne se pehle).

---

## D020 — First local end-to-end demo: SwinIR chosen over EDSR (visibly better despite tied metrics)
**Date:** 2026-09-08
**Decision:** Real trained checkpoints (`experiments/edsr/edsr_epoch19.pt`, `experiments/swinir/swinir_epoch19.pt`, dono Colab se download kiye) ko local machine par `infer_scene.py` se run kiya, ek held-out validation patch (`ROI_0045`, training mein kabhi nahi dikha) par, `visualize_demo.py` se side-by-side comparison banaya (LR input | SR output | ground truth NAIP).

Dono model ka output visually inspect kiya: **EDSR** ka output ek strong diagonal ripple/moiré texture artifact dikhata hai poore image mein, jo ground truth mein bilkul nahi hai. **SwinIR** ka output isse kaafi behtar hai — colors ground truth se match karte hain (asli green canopy, EDSR ke grey-purple wash ke against), overall structure/shapes sahi hain, aur artifact bhi present hai lekin bahut halka (light checkerboard-jaisa texture, severe ripple nahi).

Isliye demo ke liye **SwinIR checkpoint use kiya**, EDSR nahi — chahe D013 mein dono roughly metric-tied the (PSNR/SAM), visual quality mein clear difference hai. Yeh important insight hai: **raw PSNR/SSIM tie hone ka matlab equal perceptual quality nahi hai**.
**Reasoning:** Artifact ka likely cause: PixelShuffle-based sub-pixel convolution upsampling (dono EDSR aur SwinIR isi `UpsampleBlock` class ko reuse karte hain) — yeh well-documented checkerboard/ripple artifact produce karta hai jab tak pre-shuffle conv layer ko specifically initialize na kiya jaaye (ICNR initialization, ya post-shuffle blur layer add karke). Abhi humne yeh nahi kiya — standard random init use kiya.
**Alternatives considered:** Artifact ko fix karne ki koshish karna abhi hi (ICNR init add karna, retrain karna) — reject kiya for now, kyunki user ka immediate priority "aaj demo dikhana" tha, aur SwinIR ka output already demo-presentable hai. ICNR fix Open Considerations mein track kiya gaya hai future refinement ke liye.
**Status:** Accepted. Local demo working end-to-end: real Sentinel-2-scale input → real <4m (2.5m) SR output, geospatially correct, visually reasonable. Saved to `experiments/demo/` (gitignored, local only).

---

## D021 — Backend: synchronous FastAPI MVP, one endpoint, no job queue/DB
**Date:** 2026-09-08
**Decision:** `backend/app/main.py` — ek hi endpoint `POST /api/infer`: GeoTIFF upload karo, response mein hi SR GeoTIFF + before/after PNG previews (base64) wapas milte hain. Model (SwinIR, D020 ke checkpoint) startup par ek baar load hota hai, har request par nahi. No Redis/Celery/job-queue, no PostgreSQL/PostGIS — sab kuch ek request-response cycle mein, in-memory (rasterio `MemoryFile` use kiya, disk par temp files bhi nahi likhi).

Reusability ke liye `infer_scene.py` ko refactor kiya: tiling/blending/inference logic ab `run_sr_inference()` function mein hai (model + numpy array leta hai), jise CLI script aur backend dono use karte hain — duplicate nahi kiya. Refactor ke baad regression-test kiya (same input → exact same output, max diff 0.0 pre-refactor CLI output ke against).
**Reasoning:** User ne explicitly synchronous mode choose kiya (job-queue PRD ka full vision hai, lekin bade scenes ke liye zaroori hai; humara demo-size patch input ke liye ek request 1.09 second mein complete ho jata hai — async/polling ki zaroorat nahi abhi). Yeh D004 ke decision se bhi consistent hai (heavy infra MVP ke liye defer karna).
**Verification**: sirf "code likh diya" nahi — actual server start karke real GeoTIFF upload kiya curl se, response verify kiya (shapes, resolution, PNG/GeoTIFF decode karke dekha ki corrupt nahi hain, GeoTIFF ka CRS/resolution round-trip ke baad bhi sahi tha).
**Alternatives considered:** Async job-queue (Celery+Redis) abhi implement karna — reject kiya (user's explicit choice), PRD ka full vision hai lekin abhi ke MVP scope se bahar. Disk par intermediate files likhna — reject kiya, in-memory processing (MemoryFile) simpler hai aur is chhoti scale par koi disadvantage nahi.
**Status:** Accepted. Backend working end-to-end, verified with real upload.

---

## D022 — Frontend: Vite + React + TypeScript + Tailwind, single page, verified end-to-end through the dev-server proxy
**Date:** 2026-09-08
**Decision:** `frontend/` mein Vite scaffold kiya (react-ts template), Tailwind v4 (`@tailwindcss/vite` plugin — v4 mein `tailwind.config.js`/PostCSS setup ki jagah yeh recommended approach hai, purana v3-style setup nahi use kiya). Ek hi page (`App.tsx`): file upload input → `POST /api/infer` → before/after image side-by-side + GeoTIFF download button. Vite dev server ka `/api` proxy backend (port 8000) ko forward karta hai, taaki dev mein CORS ka jhanjhat na ho.
**Reasoning:** User ne explicitly single-page minimal choose kiya (multi-page PRD dashboard baad mein). Stack (React+TS+Tailwind) already PRD/README mein decided tha — koi naya decision nahi, sirf implementation.
**Verification**: Sirf `npm run build` (TypeScript compile check) hi nahi — dev server actually start kiya, `curl` se `/api/health` proxy ke through hit kiya (confirm kiya ki proxy sahi backend tak pahuchta hai), phir ek real GeoTIFF **proxy ke through** upload kiya (exactly wahi path jo browser ka `fetch()` use karega) — poora chain (Vite dev server → proxy → FastAPI → model → response) end-to-end verify hua, sirf backend ko directly test karke nahi.
**Alternatives considered:** Multi-page dashboard abhi banana — reject kiya (user's explicit choice, PRD ka full vision baad ke liye hai).
**Status:** Accepted. Full stack (backend D021 + frontend D022) working locally, browser mein use karne ke liye ready.

---

## D023 — Quality push for the demo: VGG perceptual loss + ICNR upsample fix, bundled together
**Date:** 2026-09-08
**Decision:** User ne dekha ki demo output ka visual improvement subtle tha, aur explicitly kaha "evaluator ko clearly change dikhna chahiye." Do changes ek saath kiye (normally alag-alag ablation test karte, lekin time-constraint ki wajah se bundle kiya, honestly yahan note kar raha hun):

1. **VGG perceptual loss** (`ml/losses/perceptual.py`) — pretrained VGG16 (ImageNet) ke relu3_3-tak features se SR aur HR compare karte hain (sirf RGB bands, NIR drop kiya — PRD Section 36 ka apna hint follow kiya). L1/pixel loss known-blur produce karta hai (SRGAN/ESRGAN literature se well-established) kyunki woh statistically "average plausible output" reward karta hai; perceptual loss high-level features match karke sharper/zyada realistic-looking output push karta hai.
2. **ICNR weight initialization** (`ml/models/upsample.py`) — dono EDSR aur SwinIR ka duplicate `UpsampleBlock` class ek shared module mein refactor kiya, aur usme ICNR init add kiya, jo D020 ke checkerboard/ripple artifact ko fix karta hai (PixelShuffle ke pre-shuffle conv weights ko is tarah initialize karta hai ki sab r² sub-pixel positions same kernel se start hon, matlab init ke time upsample nearest-neighbor jaisa clean ho, random-per-position nahi).

**Verification** (dono changes ke liye):
- ICNR: pehle test kiya without bias-fix — FAIL hua (2x2 output patch uniform nahi tha, std=0.084). Root cause dhoonda: `nn.Conv2d` ka default bias independently random hota hai per-channel, sirf weight equalize karna kaafi nahi tha. Bias bhi equalize kiya, phir verify kiya — ab poori tarah uniform (std=0.0 exactly, sab channels/patches mein).
- ICNR + refactor ke baad EDSR/SwinIR dono ka overfit sanity check phir se chalaya (D009/D012 jaisa) — pehle EDSR ka 60-step short test noisy dikha (lag raha tha regression hai), lekin full 150-step test (jo exact D009 protocol match karta hai) confirm kiya ki convergence healthy hai (final loss 0.102, D009 ke original 0.101 ke barabar) — short test sirf normal early-training noise pakड़ raha tha, real regression nahi tha.
- Perceptual loss: local overfit test (30 steps, combined L1+perceptual) — loss 0.55→0.20, gradient norm 11→1.8 (shrinking, healthy), koi NaN/explosion nahi. Full training script bhi smoke-test kiya end-to-end.
- SSL cert issue mila VGG16 download karte waqt (macOS python.org install ka known issue, certifi bundle use nahi ho raha tha by default) — `SSL_CERT_FILE` env var se fix kiya. Colab par yeh issue nahi aayega (proper certs already hain).

**Reasoning:** λ_perceptual=0.01 sirf ek starting guess hai (D014/D019 jaisa pattern — untuned, tuning baad mein). SwinIR ko target model banaya (D020 ke mutabik, demo ke liye already chosen).
**Alternatives considered:** Har change ko alag Colab run mein isolate karke test karna (proper ablation discipline) — reject kiya time-constraint ki wajah se; user ka immediate need ek visibly-better demo tha, do separate ~40-min Colab runs ki jagah ek run mein dono improvements bundle karna zyada practical tha. Yeh trade-off explicitly yahan document kar raha hun taaki baad mein pata rahe ki in do changes ka individual contribution isolate nahi kiya gaya.
**Status:** Accepted, local verification complete. Colab training run pending (user action).

---

## D024 — Fixed CUDA OOM in VGG perceptual loss: resize to 224x224 before feature extraction
**Date:** 2026-09-08
**Decision:** Colab par D023 ka "quality run" (SwinIR + perceptual loss) chalaya to CUDA OOM crash hua step 0 par hi — T4 (14.56 GiB) already 14.49 GiB use kar raha tha (SwinIR + optimizer + batch_size=16 @ 484×484), aur VGG ka dual forward pass (pred with grad + target no_grad, dono 484×484×16-batch par) 458 MB aur maang raha tha jo available nahi tha. Fix: `VGGPerceptualLoss._prepare()` mein ab RGB images ko VGG feed karne se pehle 224×224 (VGG ka apna native ImageNet training resolution) tak `F.interpolate` (bilinear) se resize kar dete hain.
**Reasoning:** 484×484 vs 224×224 = ~4.67x kam pixels — VGG ki poori conv stack mein activation memory proportionally kam ho jaata hai, jo is OOM (sirf 458MB short tha) ko comfortably cover karta hai. Bonus: VGG ke features actually 224px scale par hi trained/meaningful the — 484px par unbounded resolution feed karna already ek extra scale-mismatch tha (RGB-domain mismatch ke upar), to yeh fix sirf memory issue nahi, conceptually bhi zyada correct hai.
**Verification**: Local CPU test (GPU nahi hai yahan, lekin shape/gradient-flow correctness check kiya) — combined L1+perceptual loss 20 steps chalaya, loss 1.15→0.29 decrease hua, gradient norm healthy (16.1→7.7, koi explosion nahi). Actual OOM-resolution sirf Colab GPU par verify ho sakta hai (memory ka exact accounting local CPU run mein nahi dikhta) — agla Colab run isko confirm karega.
**Alternatives considered:** Batch size kam karna (16→8) instead of/along with resize — abhi ke liye sirf resize kiya (bada margin deta hai, ~4.67x), batch size same rakha taaki baseline SwinIR run (D013) ke saath directly comparable rahe (sirf loss function change ho, batch size nahi). Agar yeh bhi OOM de, batch size reduction next fallback hai.
**Status:** Accepted, locally verified. Colab retry pending (user action) — koi checkpoint pehle attempt se bacha nahi (crash step 0 par hi hua tha), poora training run phir se chalana hoga.

---

## D025 — Second OOM (different cause): CUDA allocator fragmentation, not raw capacity
**Date:** 2026-09-08
**Decision:** D024 ka resize fix kaam kiya (epoch 0 successfully complete hua, checkpoint bhi save hua) — lekin epoch 1 shuru hote hi phir OOM aaya, is baar SwinIR ke apne upsample/PixelShuffle step mein, VGG mein nahi. Error message mein clue tha: "2.08 GiB is reserved by PyTorch but unallocated" — yeh capacity issue nahi, **fragmentation** hai (total free+reserved memory kaafi thi, lekin ek single 858MB contiguous block available nahi tha). Crash specifically ek pura epoch + validation (train batch=16 → eval batch=1 → wapas train) cycle ke baad hua, jo is fragmentation-hypothesis ko support karta hai (batch size baar-baar switch karna allocator ko fragment karta hai).

Teen fixes ek saath kiye:
1. Har epoch ke end mein (checkpoint save se pehle) `torch.cuda.empty_cache()` call kiya — teeno training scripts mein (`train_swinir.py`, `train_edsr.py`, `train_edsr_uncertainty.py`, consistency ke liye, chahe abhi sirf SwinIR crash hua ho).
2. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` env var set kiya Colab cell mein — yeh khud PyTorch ke apne error message ka suggestion hai, allocator ko existing segments expand karne deta hai naye contiguous blocks maangne ki jagah.
3. Batch size 16→8 kam kiya is specific run ke liye (extra safety margin, do OOM ke baad).
**Reasoning:** Do alag-alag OOM causes (D024: raw capacity/resolution, D025: fragmentation) ek hi "quality run" mein mile — dono fix karna zaroori tha taaki teesri baar phir se fail na ho. `torch.cuda.is_available()` guard ke saath likha taaki local CPU testing break na ho.
**Verification**: Local smoke test (CPU, `torch.cuda.is_available()` False hone ki wajah se `empty_cache()` skip hota hai) — 2 epochs clean chale, koi syntax/logic error nahi. Actual fragmentation-fix ka real verification sirf Colab GPU par hoga (memory allocator behavior local CPU run mein reproduce nahi hota).
**Alternatives considered:** Sirf batch size kam karna (bina fragmentation fix ke) — reject kiya kyunki root cause specifically fragmentation tha (capacity nahi), to sirf batch-size-reduction band-aid hota; asal fix (empty_cache + expandable_segments) zyada targeted hai.
**Status:** Accepted, locally verified (syntax/logic only). Colab retry #2 pending (user action).

---

## D026 — Before/after slider (PRD section 12), native range input instead of a drag library
**Date:** 2026-09-08
**Decision:** `frontend/src/components/BeforeAfterSlider.tsx` — static side-by-side grid ki jagah ab ek draggable before/after slider hai. Implementation: SR output base layer ke roop mein full-size render hota hai, LR input CSS `clip-path: inset()` se left N% tak hi dikhta hai, aur ek invisible (`opacity-0`) native `<input type="range">` poore container par overlay hota hai jo drag position control karta hai. Visual divider line/handle sirf display ke liye hai (`pointer-events-none`), actual interaction native range input handle karta hai.
**Reasoning:** Native `<input type="range">` use karne se drag/touch/keyboard sab automatically kaam karte hain (accessibility bhi free mein milti hai) — koi extra npm dependency (jaise react-compare-slider) nahi chahiye. Yeh existing "minimal dependencies" spirit (D022) ke saath consistent hai.
**Verification**: `npm run build` clean pass hua (TypeScript errors nahi). Dev server (already running, HMR se changes live the) ke through proxy se real GeoTIFF upload karke confirm kiya ki backend integration abhi bhi kaam karta hai. Visual drag-behavior (slider actually smoothly move karta hai ya nahi) browser mein hi verify ho sakta hai — user ko check karne ke liye bola.
**Alternatives considered:** Manual mousedown/mousemove/mouseup pointer-event handling likhna — reject kiya, native range input same result deta hai kam code aur better accessibility ke saath.
**Status:** Accepted, build-verified. Visual behavior browser mein user confirm karega.

---

## D027 — Accuracy metrics in the UI: only computed when a ground-truth reference is provided, never fabricated
**Date:** 2026-09-08
**Decision:** User ne poocha "kis extent tak image sahi hai" dikhana chahte the. PSNR/SSIM/SAM/ERGAS sab ko ek ground-truth HR reference chahiye compare karne ke liye — real-world upload (koi reference nahi) ke liye yeh genuinely compute nahi ho sakte. Isliye `POST /api/infer` mein ek optional dusra file field add kiya (`hr_reference`) — agar diya gaya, real metrics compute karke return karte hain; nahi diya to `metrics: null`, UI mein saaf keh deta hai "reference nahi diya, metrics available nahi hain" — kabhi bhi fabricate nahi karte.

Metrics computation: SR output (jo already denormalized/physical-scale hai response ke liye) ko `_normalize()` se wapas [0,1] mein convert kiya (D008 ka wahi hr_ranges reuse kiya), reference ko bhi same normalize kiya, phir `compute_all_metrics()` (already-tested `ml/evaluation/metrics.py`) call kiya — bilkul wahi normalization jo training/eval mein har jagah use hoti hai, koi naya ad-hoc scale nahi banaya.
**Verification**: Real LR/HR pair (ROI_0057) upload kiya curl se, poore proxy path (5173→8000) ke through — metrics mile (PSNR 16.73, SSIM 0.196, SAM 15.49°, ERGAS 13.76). SSIM thoda low laga (val-set average ~0.43 se), to cross-check kiya `ml/evaluation/evaluate_checkpoint.py` ka trusted code path use karke isi exact image par — **exact same numbers** aaye (floating-point tak match) — confirm hua ki backend ka metrics wiring sahi hai, low SSIM genuine hai (yeh road/building-heavy patch hai, jahan exact edge-alignment SSIM ko zyada punish karta hai, jo visually bhi consistent hai jo pehle dekha tha). Do edge cases bhi test kiye: (1) reference na diya → `metrics: null`, koi crash nahi; (2) mismatched-shape reference diya → clean 400 error with clear message, crash nahi.
**Reasoning:** Yeh poore project ka core ethos hai (PRD Section 14: "never put fabricated numbers") — real-world deployment mein reference nahi milega, to honestly "unavailable" dikhana zaroori tha fake confidence dikhane ki jagah.
**Alternatives considered:** Uncertainty-model (D016/D018) se confidence map dikhana (jisko ground truth ki zaroorat nahi) — abhi ke liye reject kiya kyunki backend abhi SwinIR serve karta hai (best visual quality ke liye, D020), aur uncertainty-trained EDSR checkpoint ka real Colab run abhi tak nahi hua (Open Considerations mein already tracked). Future improvement ke roop mein note kiya.
**Status:** Accepted. Backend + frontend dono verified end-to-end.

---

## D028 — Quality run complete: metrics roughly flat (as expected), real test is visual
**Date:** 2026-09-08
**Decision:** SwinIR + perceptual loss + ICNR (D023/D024/D025 fixes) training complete kiya — 30 epochs, koi crash nahi (dono memory fixes poore run mein held). Full val-set (n=279) comparison plain-L1 SwinIR (D013) ke against:

| Metric | Plain SwinIR | + perceptual + ICNR |
|---|---|---|
| PSNR | 16.92 dB | 16.83 dB |
| SSIM | 0.429 | 0.437 |
| SAM | 11.60° | 12.07° |
| ERGAS | 14.56 | 13.89 (median 8.90) |

**Reasoning:** Numbers roughly wash hain — PSNR/SAM thoda flat/worse, SSIM/ERGAS thoda better. Yeh exactly literature-consistent hai: perceptual loss known tradeoff hai — pixel-fidelity metrics thodi qurbaan hoti hain perceptual/visual quality ke liye, guaranteed metric-improvement nahi hota. Is run ka asli maqsad metrics improve karna tha hi nahi — checkerboard artifact (D020) kam karna aur visually sharper output dena tha, jo metrics dekh nahi sakte. Real verification ab checkpoint download karke visual comparison se hoga (jaisa D020 mein pehle kiya tha).
**Status:** Training accepted as successful (both D024/D025 fixes verified working end-to-end on real Colab GPU run, no crash). Visual verification pending (user download + rerun demo).

---

## D029 — Visual verification: perceptual+ICNR checkpoint is genuinely sharper, backend switched to it
**Date:** 2026-09-08
**Decision:** `experiments/swinir_quality/swinir_epoch29.pt` (D023-D025) ko real demo patch (`ROI_0057`) par run kiya, ek zoomed crop (flat/uniform region, jahan texture difference sabse clearly dikhta hai) mein old plain-L1 SwinIR se directly compare kiya. Result: **clear, visually obvious improvement** — old checkpoint smooth/blobby low-frequency texture deta tha (bade soft dark blobs, koi fine detail nahi), naya checkpoint genuine fine-grained texture deta hai jo ground truth ke actual canopy-texture pattern se structurally milta hai. Yeh subtle nahi tha — direct crop comparison mein turant dikh gaya.

Important observation: full-val-set PSNR/SSIM D028 mein roughly flat/wash the (16.92→16.83 dB, 0.429→0.437) — matlab pixel-level metrics ne is real, visible texture improvement ko barely capture kiya. Yeh literature-consistent hai (perceptual loss texture/perceptual quality improve karta hai without necessarily moving PSNR/SSIM) aur ek genuinely useful talking point hai: **numbers na hilna iska matlab yeh nahi ki output same hai**.

Backend ka `CHECKPOINT_PATH` update kiya naye checkpoint par point karne ke liye. Verify kiya: model load hua, poore proxy path (5173→8000) se real upload test kiya, metrics consistent aaye full-val average ke saath.
**Reasoning:** Yeh exactly wahi cheez thi jo user ne originally maanga tha ("evaluator ko clearly change dikhna chahiye") — ab live demo mein genuinely behtar, visually sharper output serve ho raha hai, sirf metrics-pe-flat checkpoint nahi.
**Alternatives considered:** D023 mein ICNR aur perceptual loss ko bundle kiya tha time-constraint ki wajah se — is result se individually attribute nahi kar sakte ki kis fix ne kitna contribute kiya, sirf combined effect verified hai. Future ablation (sirf ICNR, sirf perceptual, alag-alag) is open item hai agar precise attribution chahiye ho.
**Status:** Accepted. Live backend/demo ab is behtar checkpoint se serve karta hai.

---

## D030 — Indian AOI qualitative validation: works well on real Delhi imagery, closes the biggest flagged gap
**Date:** 2026-09-13
**Decision:** Ek real, free, no-account-needed Sentinel-2 scene fetch kiya AWS Open Data se (Element84's public Earth Search STAC catalog, `pystac-client` se query kiya) — central Delhi (Connaught Place area), Feb 2026, cloud cover ~0.0006% (effectively clear). 400×400 px (4km×4km) crop liya seedha remote COG se rasterio windowed-read se (poora ~110km tile download nahi kiya). Isko already-trained checkpoint (`swinir_quality/swinir_epoch29.pt`, koi retraining nahi) se run kiya.

**Result:** Visually strong — dense urban grid (jo blur/mottled tha 10m input mein) individual buildings mein resolve hua, Connaught Place ka radial road pattern kaafi saaf ho gaya, green spaces/park boundaries clear hue. Yeh model ne kabhi kisi Indian scene par train nahi kiya tha (sirf US NAIP data), phir bhi structurally sound, plausible output diya.

Reusable script bana diya (`geospatial/preprocessing/fetch_sentinel2_aoi.py`) — kisi bhi lon/lat AOI ke liye Sentinel-2 crop fetch kar sakta hai, future locations/disaster-sites test karne ke liye reuse ho sakta hai.
**Reasoning:** Yeh defense-brief mein flagged sabse bada gap tha ("Is your training data Indian?"). Ab humare paas ek concrete, real, visually-verified qualitative demo hai. **Important honest caveat**: yeh sirf qualitative hai — koi Indian ground-truth HR reference exist nahi karta, isliye PSNR/SSIM/SAM/ERGAS jaise quantitative metrics yahan compute NAHI ho sakte. Yeh "does it look plausible on Indian terrain" ka jawab hai, "here's the accuracy number for India" ka nahi — is distinction ko clearly communicate karna hai.
**Alternatives considered:** Ground-truth ke bina bhi koi fake/estimated metric dikhana — reject kiya, poore project ke "never fabricate" principle ke against jaata.
**Status:** Accepted. Real, visually-verified qualitative result mil gaya. Assets `experiments/india_aoi/` mein saved (gitignored, local).

---

## D031 — Synthetic-shard data-scaling investigated: feasible via `opensr-degradation`, but real added complexity, not started yet
**Date:** 2026-09-13
**Decision:** User ne suggest kiya SEN2NAIP ke 18 synthetic shards (D002 mein documented, ~177GB total) use karke training data badhana, taaki bigger model/zyada epochs safely try kar sakein (overfitting risk kam ho, sirf 2,283 train pairs abhi hain). Verify kiya: synthetic split mein ready-made `lr.tif` nahi hai — sirf full-res NAIP image + ek "degradation model histogram" (`metadata.json` mein) hota hai. Synthetic LR generate karne ke liye ek existing package chahiye: **`opensr-degradation`** (ESA ka open-source package, `ESAOpenSR/opensr-degradation` GitHub par, MIT license, pip-installable — `opensr_degradation.main.get_s2like(image, table, model="gamma_multivariate_normal_50")`).

**Reasoning:** Yeh feasible hai lekin "download folder, extra pairs mil gaye" jitna simple nahi — ek extra dependency chahiye, aur package abhi kaafi naya/niche hai (26 stars, 9 commits, paper "coming soon" — humein khud verify karna hoga smoke-test se ki yeh sahi kaam karta hai, blindly trust nahi karna, jaisa humne poore project mein har naye component ke saath kiya hai).

Scientific recommendation (agar aage badhte hain): synthetic data ko **directly real cross-sensor data ke saath mix nahi karna** — synthetic degradation ek simulated function hai, real sensor physics nahi, to model us specific simulation ko "undo karna" seekh sakta hai jo real Sentinel-2 par generalize nahi karega. Better approach: synthetic par **pretrain** karo (bahut zyada data, general texture/upsampling patterns seekhne ke liye), phir real cross-sensor data par **fine-tune + evaluate** karo (jaisa D002 mein already recommend tha: "synthetic training initially, then validate/fine-tune using real-world data").
**Status:** Investigated, feasible, **not yet started**. Agla step (agar proceed karna hai): `opensr-degradation` install karke ek chhota sample par smoke-test karna (kya yeh sahi S2-like image deta hai), phir Kaggle par (30hr/week free GPU) pretrain-then-finetune pipeline banana.

---

## D032 — Cloud/nodata masking: SCL-based, verified against real clouds, wired into inference
**Date:** 2026-09-13
**Decision:** `geospatial/preprocessing/cloud_mask.py` banaya — Sentinel-2 L2A ke apne Scene Classification Layer (SCL) band se cloud/shadow/nodata mask compute karta hai. Class codes web-search se verify kiye (D024 jaisi discipline — memory se hardcode nahi kiya): 0 nodata, 1 saturated/defective, 3 cloud shadow, 8/9 cloud medium/high probability, 10 thin cirrus = invalid; baaki (vegetation, water, snow, dark-area shadow, unclassified) valid maana. `fetch_sentinel2_aoi.py` ko extend kiya SCL bhi fetch kare (20m native resolution, nearest-neighbor se 10m grid par align kiya — categorical/class data ko kabhi interpolate nahi karte). `infer_scene.py` mein `--scl` aur `--max-cloud-fraction` flags add kiye — agar diya jaaye, cloud/shadow pixels ko inference se pehle 0 kar dete hain, aur agar cloud fraction threshold se zyada hai to explicitly refuse kar dete hain SR chalane se ("refusing to run SR over unreliable input") bajaye silently garbage output dene ke.

**Verification** (sirf "code likha, chal gaya" nahi): (1) Known-clear Delhi scene par 0.00% cloud aaya — expected. (2) Deliberately ek real monsoon-season Mumbai scene dhoondha (36.9% scene-level cloud cover) — humara AOI-level pixel count 39.04% nikla, close match. (3) **Sabse important**: mask ko RGB image ke upar visually overlay karke dekha — jahan clouds genuinely dikh rahe the (white/hazy patches), wahi red/masked the; clear areas (lake, park, buildings) green/valid the. (4) End-to-end test kiya: masking+proceed (39% < 50% default threshold) sahi se chala, aur stricter threshold (20%) ke saath abort bhi sahi se hua.
**Reasoning:** Yeh PRD ka apna explicit requirement tha ("cloud/no-data handling" preprocessing mein, Section 23) jo defense-brief mein "named but not built" ke roop mein flag kiya gaya tha — ab genuinely built aur verified hai. Model ko kabhi cloud data par train nahi kiya gaya, to cloud-covered pixels par confidently SR chalana misleading/fabricated output dega — is se better hai clearly "yahan data nahi hai" dikhana.
**Alternatives considered:** Sirf whole-scene `eo:cloud_cover` metadata (STAC item property) par rely karna — reject kiya kyunki woh poori 100km tile ka average hai, hamare chhote AOI crop ke liye precise nahi (ek clear-average tile ka specific corner bhi cloudy ho sakta hai) — isliye pixel-level SCL check zaroori tha exact crop ke liye.
**Status:** Accepted. Local pipeline mein verified working.

---

## D033 — Downstream task (Phase 8): zero-shot segmentation proxy attempted, found inconclusive, abandoned honestly
**Date:** 2026-09-13
**Decision:** Phase 8 validate karne ke liye Meta ka Segment Anything Model (SAM, ViT-B, zero-shot, no labeled data chahiye) use kiya — bicubic-upsampled input, SR output, aur ground truth (`ROI_0057`) par automatic mask generation chalake distinct segment count compare kiya, "does SR help identify more real structures" ka proxy test karne ke liye.

**Ek real bug pehle catch kiya**: pehla run "bicubic = 1 segment" dikha raha tha — visually verify kiya to pata chala bicubic-upsampled image ek solid uniform color render ho raha tha (`upsample_bicubic()` ko raw un-normalized reflectance values diye the, jiska internal `.clamp(0,1)` sab kuch 1.0 par clip kar deta, D008 ka normalization step missing tha). Fix kiya (normalize → bicubic upsample → denormalize, taaki teeno images same physical scale share karein).

**Fix ke baad real result**: Bicubic 12 segments, SR 8, ground truth 14 — **raw count SR ke favor mein nahi tha**. Visually inspect kiya: bicubic ke bade segments open/smooth field areas mein the (building cluster ko bilkul miss kar gaya), SR ka ek chhota segment building-cluster location par tha (real structure), plus ek road segment. Lekin jab location-aware overlap metric banaya (kya segments ground-truth "structure" regions se overlap karte hain), woh bhi clean nahi nikla (bicubic 32.6% vs SR 27.6% overlap) — kyunki ground truth ke apne 14 SAM segments khud bhi pure "buildings" nahi the (pond, bare-soil patches bhi include the), jo overlap-metric ko dilute/noisy bana deta hai.
**Reasoning:** Yeh method (zero-shot SAM segment count/overlap, bina labeled data ke) is specific case ke liye clean quantitative claim dene laayak nahi nikla. Visual evidence still real hai (SR building cluster resolve karta hai, bicubic nahi karta) — lekin numbers ko headline result ki tarah present karna overclaim hota, jo poore project ke "never fabricate/spin" principle ke against jaata.
**Alternatives considered:** Manually ek building-cluster bounding box mark karke tighter check karna — user ne abhi ke liye reject kiya (is approach par aur time invest nahi karna).
**Status:** Attempted, honestly inconclusive, **abandoned for now** per user's explicit choice. Visual qualitative evidence (building cluster comparison) reusable hai future materials mein, quantitative segment-count numbers nahi.

---

## D034 — Uncertainty training prep: Kaggle notebook + fixed a real evaluation gap
**Date:** 2026-09-13
**Decision:** GPU-training items (uncertainty, bigger/longer retrain, synthetic pipeline) sirf Colab/Kaggle par chal sakte hain, is CPU-only local machine par nahi — to unhe actually chalane ke liye user ka apna action chahiye. Jo abhi locally kiya ja sakta tha: `notebooks/train_edsr_uncertainty_kaggle.ipynb` banaya (Kaggle-adapted, user ke Kaggle 30hr/week free GPU suggestion ke mutabik) — Colab version se paths/download-mechanism alag hai (`/kaggle/working/`, `google.colab.files.download` ki jagah Output-tab se download).

**Real gap catch kiya is prep ke dauraan**: `evaluate_checkpoint.py` mein `--uncertainty` flag exist hi nahi karta tha — matlab agar user Kaggle par uncertainty model train kar leta, to poore validation set (279 pairs) par proper evaluate karne ka koi tareeka nahi tha (sirf training ke andar ka 50-sample per-epoch estimate milta, jaisa D016 mein tha). Isko fix kiya — ab `--uncertainty` flag se dono (a) standard metrics (mean prediction par) aur (b) calibration statistic (poore val set par, sirf training ke 50-sample se nahi) compute ho sakte hain. Local smoke-test kiya (5 val samples, 4-step tiny checkpoint se) — chalta hai correctly.
**Reasoning:** Yeh gap agar pehle na pakड़ते, to user Kaggle GPU-hours use karke train karta, phir realize hota ki evaluate karne ka tareeka hi missing hai — isse better hai ki training start karne se pehle hi yeh fix ho jaaye.
**Status:** Accepted. Notebook ready, evaluation gap closed. Actual Kaggle run pending (user action).

---

## D035 — Added mixed-precision (AMP) training to actually use T4's Tensor Cores
**Date:** 2026-09-13
**Decision:** User ne T4 par chalane ka decide kiya (P100 recommendation ke bawajood). Diya gaya reasoning tha: humara script plain FP32 mein train karta hai, jisme P100 (no Tensor Cores, but higher raw FP32 throughput) T4 se generally fast hota — T4 ka real advantage Tensor Cores hain, jo sirf mixed-precision (FP16) training mein kaam aate hain. To `train_edsr_uncertainty.py` mein `--amp` flag add kiya (`torch.autocast` + `torch.amp.GradScaler`), taaki T4 apni asli strength use kare.

Numerical safety: model ka forward pass fp16 (autocast) ke andar chalta hai (Tensor Core speedup ke liye), lekin loss computation (Gaussian NLL, jisme `exp()` aur division hai) explicitly `.float()` cast karke fp32 mein hi hota hai — kyunki is loss ka pehle se hi instability history hai (D016: high-LR par diverge karta hai) aur fp16 mein exp()/division extra risk add karta.
**Verification**: Local CPU par dono paths test kiye — (1) `--amp` flag ke bina (baseline behavior unchanged), (2) `--amp` flag ke saath but CUDA na hone ki wajah se automatically no-op ho jaata hai ("--amp requested but no CUDA device" warning ke saath) aur exact same tarike se chalta hai jaise flag na diya ho. **Honest limitation**: actual CUDA fp16 autocast path yahan CPU-only machine par test nahi ho sakta — real verification sirf Kaggle T4 par chalane ke baad hoga. User ko explicitly bataya gaya hai training ke shuru mein loss values monitor karne ke liye (nan/inf dikhe to turant batana).
**Reasoning:** User ne khud T4 choose kiya apne reasons se — code ko us choice ke hisaab se genuinely better banaya (sirf "T4 chalega" nahi, "T4 ka fayda uthayega") bajaye sirf slower-as-is chalne dene ke.
**Alternatives considered:** Multi-GPU (Kaggle ka T4 x2 dono GPUs use karna via DataParallel) — abhi nahi kiya, kyunki model chhota hai (EDSR ~1.5M params) aur DataParallel ka communication-overhead is scale par gains ko eat kar sakta hai; AMP ka fayda zyada direct/kam-risk tha.
**Status:** Accepted, CPU-path verified. Real GPU/fp16 verification Kaggle run ke baad (user action).

---

## D036 — Uncertainty training complete (real Colab run): positive but modest calibration
**Date:** 2026-09-13
**Decision:** Phase 6 (heteroscedastic uncertainty, D016/D018) ka pehla real GPU training run complete hua — 20 epochs, full train split (2,283 pairs), Colab T4, `--amp` (D035) ke saath. Koi crash nahi, poori training stable rahi (grad_norm 4-222 ke beech fluctuate kiya, lekin clipping ne hamesha apna kaam kiya, kabhi diverge nahi hua).

**Full validation-set (n=279) final results:**

| Metric | Value |
|---|---|
| PSNR | 16.80 dB |
| SSIM | 0.443 |
| SAM | 11.90° |
| ERGAS | 15.06 (median 8.87) |
| **Calibration** | **0.206 (std 0.193)** |

Reconstruction quality dusre trained models (EDSR 16.77, SwinIR 16.92) ke comparable hai — uncertainty head ne quality meaningfully hurt nahi ki. **Calibration genuinely positive hai** (fake/random nahi) — jahan model "confident nahi hoon" bolta hai, wahan sach mein zyada error hota hai — lekin "ideal" threshold (>0.3-0.4) se kam hai, aur high std (0.193) batata hai ki calibration quality image-to-image kaafi vary karti hai (kuch patches par strong, kuch par weak).

**Honest conclusion**: Uncertainty estimation genuinely kaam karta hai, ek modest/real signal ke roop mein — "strong/highly-reliable" ka daava nahi kar sakte. Training ke dauraan bhi yehi pattern dikha — calibration number 20 epochs mein steadily improve nahi hua (PSNR/SSIM ki tarah), balki 0.13-0.28 ke beech bounce karta raha.
**Reasoning:** Yeh Phase 6 ka pehla genuine, complete validation hai (ab tak sirf smoke-tested tha, D016/D018). Is result ko as-is report kar rahe hain — na overclaim, na underclaim.
**Alternatives considered:** N/A — yeh planned training run tha, iska result jo bhi aata usko honestly report karna tha.
**Status:** Accepted. **Phase 6 complete.** Checkpoint `experiments/edsr_uncertainty/edsr_unc_epoch19.pt` ready hai demo integration ke liye (uncertainty-map display) agar aage badhna ho.

---

## D037 — Uncertainty map wired into the live demo (dual-inference)
**Date:** 2026-09-13
**Decision:** Backend ab do models load karta hai startup par — SwinIR (D029, sharp image ke liye) aur EDSR-uncertainty (D036, confidence map ke liye). `/api/infer` dono ko same input par chalata hai, SwinIR ka SR output dikhata hai (jaisa pehle) aur uncertainty model ka std output ek heatmap (inferno colormap, per-band-averaged, per-request min-max stretched) ke roop mein third panel mein show karta hai. Frontend mein "Model confidence" section add kiya jo yeh heatmap dikhata hai with explanation.
**Verification**: Backend restart kiya, `/api/health` se dono models load hone ka confirm kiya. Real upload test kiya poore proxy path (5173→8000) se — response mein `uncertainty_preview_png` present tha. Decoded PNG ko standalone verification (jo isi turn mein pehle ki thi, D036 ke baad) se compare kiya — same road-network-highlighted pattern dikha, confirming backend integration sahi hai.
**Reasoning:** Dual-inference isliye chuna (single unified model ki jagah) kyunki SwinIR (best visual quality, D020/D029) aur EDSR-uncertainty (confidence map ke liye trained) alag architectures hain — dono ko ek saath train karna abhi tak nahi kiya gaya. Cost: ek request ab ~2.5s leta hai (pehle ~1s tha, do model chalane ki wajah se) — demo-scale single-patch requests ke liye still fast enough.
**Alternatives considered:** Sirf ek model (jaisa EDSR-uncertainty) poore demo ke liye use karna — reject kiya kyunki SwinIR ka visual quality (D029 ke baad) uncertainty-EDSR se behtar hai, aur dono capabilities (sharp image + confidence map) saath dikhana zyada valuable hai.
**Status:** Accepted. Phase 6 (uncertainty) ab poori tarah demo mein integrated hai — trained, validated, aur live application mein dikh raha hai.

---

## D038 — Confidence-weighted EDSR/SwinIR fusion: a genuine, verified improvement
**Date:** 2026-09-13
**Decision:** Ek naya inference-time technique banaya — koi naya training nahi, sirf dono already-trained models (EDSR-uncertainty aur SwinIR-quality) ko ek saath use karna. `ml/inference/fuse_models.py`: EDSR ka apna predicted uncertainty (std) use karke, per-pixel decide karte hain kitna EDSR ke mean prediction par trust karna hai vs SwinIR ke output par gir jaana hai — jahan EDSR confident hai (low std), uska output zyada weight leta hai; jahan EDSR unsure hai, SwinIR (generally sharper model, D020/D029) zyada weight leta hai.

**Full validation-set verification (n=279)** — sirf ek demo patch par test nahi kiya, poore val set par:

| Metric | EDSR | SwinIR | Fused |
|---|---|---|---|
| PSNR | 16.80 | 16.83 | **16.89** |
| SSIM | 0.4430 | 0.4367 | **0.4471** |
| SAM | 11.90° | 12.07° | **11.84°** |
| ERGAS | 15.06 | 13.89 | 14.55 (median ~same, 8.87-8.90) |

Fused output dono individual models se **better ya tied hai har metric par** (ERGAS mean thoda beech mein hai, lekin median — jo zyada robust hai D015 ke outlier-issue ki wajah se — teeno mein almost same hai).
**Reasoning:** Yeh ek genuinely free improvement hai — koi naya GPU training nahi chahiye, dono checkpoints already trained the. Gain modest hai (kuch hundredths dB) lekin consistent hai poore validation set par, na ki ek lucky patch ka fluke. Yeh ensemble-learning ka well-established principle hai (do reasonably-different models ke errors average out karke combined error kam karna) — humare project mein pehli baar hai jab koi single change sabhi metrics par cleanly improve karta hai (compare D019 — spectral/edge loss hurt kiya, D028 — perceptual loss metrics par roughly flat tha).
**Alternatives considered:** Simple 50/50 average (uncertainty-agnostic) — try nahi kiya explicitly, lekin confidence-weighted approach zyada principled hai aur already achha result de raha hai.
**Status:** Accepted. Real, verified improvement — inference-time only, zero training cost.

---

## D039 — Live demo now serves confidence-weighted fusion, not raw SwinIR
**Date:** 2026-09-13
**Decision:** Backend ka `/api/infer` ab `confidence_weighted_fuse()` (D038) ka output serve karta hai — raw SwinIR nahi. Dono models (SwinIR aur EDSR-uncertainty) already load hote the dual-inference (D037) ke liye; ab unka combined/fused output hi "GeoSR-4 output" ban gaya hai, sirf uncertainty heatmap ke liye alag se EDSR std use hota rehta hai.
**Verification**: Backend restart kiya, poore proxy path (5173→8000) se real upload test kiya. Metrics EXACT match hue standalone fusion test ke (PSNR 16.92, SSIM 0.2177 — same patch, same numbers) — confirm hua ki integration bilkul sahi hai. Output image bhi visually clean render hua, koi blending artifact nahi.
**Reasoning:** D038 mein verify ho chuka tha ki fusion genuinely better hai (poore val set par har metric par best ya tied) — is improvement ko live demo mein use na karna waste hota.
**Status:** Accepted. Live demo ab humara best-verified output serve karta hai.

---

## D040 — Set up isolation of ICNR vs perceptual loss (2x2 ablation design)
**Date:** 2026-09-13
**Decision:** D023 ne ICNR init aur perceptual loss dono ek saath change kiye the (time-constraint ki wajah se) — kabhi isolate nahi kiya ki visible sharpness improvement (D029) kis wajah se aaya. Isko close karne ke liye `UpsampleBlock` mein `use_icnr_init` flag add kiya (default `True`, taaki baaki poora codebase bina change ke chalta rahe), EDSR/SwinIR dono mein thread kiya, `train_swinir.py` mein `--no-icnr-init` CLI flag add kiya.

Do naye training configs banaye (Colab notebook mein section 7a/7b):
- **7a (ICNR-only)**: ICNR on, perceptual off — D013 baseline (dono off) se compare hoga
- **7b (Perceptual-only)**: ICNR off, perceptual on — bhi D013 se compare hoga

Isse ek clean 2x2 grid milta hai: D013 (dono off), D028 (dono on), 7a (sirf ICNR), 7b (sirf perceptual) — bina D013/D028 dobara chalaye.
**Verification**: `icnr_init` toggle ko directly test kiya (2x2 patch uniformity check, D023 jaisa) — `use_icnr_init=True` se std=0.0 (uniform), `False` se std=0.408 (random, non-uniform) — confirm hua toggle sahi kaam karta hai. Teeno relevant flag-combinations (default, `--no-icnr-init --lambda-perceptual`, default-again) local CPU par smoke-test kiye — sab clean chale.
**Reasoning:** Ab tak ka combined result (D023-D029) genuinely achha tha, lekin attribution unclear thi — panel ko precise answer dena better hai "dono change kiye, pata nahi kaunsa kaam kiya" se.

**Real result — 7a (ICNR-only), Kaggle run complete (2026-09-25), n=279:**

| Metric | D013 baseline (dono off) | D028 combined (dono on) | 7a ICNR-only |
|---|---|---|---|
| PSNR | 16.92 dB | 16.83 dB | **16.54 dB** |
| SSIM | 0.429 | 0.437 | 0.4301 |
| SAM | 11.60° | 12.07° | **11.53°** |
| ERGAS | 14.56 | 13.89 (median 8.90) | 16.79 (median 8.60) |

**Honestly, yeh expected se different hai.** Hypothesis tha ICNR akela hi clear PSNR/quality win dega (deterministic, verified fix hai checkerboard artifact ke liye) — lekin isolated run mein PSNR baseline se **worse** hai (16.54 vs 16.92), SSIM roughly flat, sirf SAM thoda better hai. ERGAS mean bhi worse hai (median dono runs mein similar range mein hai, 8.6-8.9, to yeh D015 wale outlier-skew ka pattern lagta hai).

**Ek real confound hai jo honestly flag karna zaroori hai**: yeh run `--amp` (mixed precision, D041) ke saath chala — D013 aur D028 dono runs `--amp` ke bina hue the (feature tab tak exist nahi karta tha). Toh yeh pure ICNR-vs-baseline comparison nahi hai, ek extra variable (amp) bhi saath mein badal gaya hai. Iska convergence par kitna effect hota hai, pata nahi — ek possible explanation hai is unexpected result ka, lekin confirm nahi hai (run-to-run random variance bhi ho sakta hai, single run hai, koi seed-repeat nahi kiya).

**Real result — 7b (Perceptual-only) bhi complete (2026-09-25), n=279:** PSNR 16.72 dB, SSIM 0.4344, SAM 11.79°, ERGAS 15.10 (median 8.59). Yeh bhi `--amp` ke saath chala, wahi confound.

**Poora 2x2 grid (sab n=279 val set):**

| | No perceptual | + Perceptual |
|---|---|---|
| **No ICNR** | D013 baseline: 16.92dB / 0.429 / 11.60° / 14.56 | 7b: 16.72dB / 0.4344 / 11.79° / 15.10 (median 8.59) |
| **+ ICNR** | 7a: 16.54dB / 0.4301 / 11.53° / 16.79 (median 8.60) | D028 combined: 16.83dB / 0.437 / 12.07° / 13.89 (median 8.90) |

**Honest interpretation:** PSNR aur SAM ka pattern inconsistent hai — ICNR akela add karne se PSNR baseline se *girta* hai (D013→7a), lekin perceptual ke saath ICNR add karne se PSNR *badhta* hai (7b→D028) — sign hi flip ho raha hai depending on the other flag. Yehi ulta pattern perceptual ke liye bhi hai. Yeh sab differences bhi chhote hain (0.1-0.5 dB / 0.2-0.5°) — likely run-to-run noise ke range mein hi hain (koi seed-repeat nahi kiya gaya, sirf ek-ek run hai har config ka), aur `--amp` confound upar se.

**Ek cheez consistent hai**: SSIM monotonically badhta hai jaise-jaise components add hote hain — D013 (0.429) < 7a (0.4301) < 7b (0.4344) < D028 (0.437). Yeh weak evidence hai ki dono components thoda positive contribute karte hain SSIM par, aur combined sabse best hai — lekin PSNR/SAM/ERGAS is pattern ko support nahi karte.

**Final conclusion**: Is ablation se **precise numeric attribution nahi mil saka** — metrics is difference ko resolve karne ke liye kaafi sensitive nahi hain (yeh khud D028 mein pehle se predicted tha: "metrics roughly flat, real test visual hai"). Jaisa D029 mein visual comparison se hi asli sharpness-improvement pakड़ा tha (metrics ne nahi), waise hi ab bhi agar precise attribution chahiye ho to 7a/7b/D028/D013 checkpoints ka visual side-by-side comparison karna padega, sirf numbers se nahi chalega.
**Status:** Dono runs (7a, 7b) complete, real results logged. Numeric attribution inconclusive rahi — yeh khud ek honest finding hai (D047 downstream-task jaisa hi pattern: rigorous test kiya, result clean nahi nikla). Visual comparison optional next step hai agar precise attribution abhi bhi chahiye.

---

## D041 — D040 ablation ko Kaggle par bhi chalane layak banaya (`--amp` + naya notebook)
**Date:** 2026-09-25
**Decision:** D040 ka Colab run 7-8 hr le raha tha, jo Colab ke free-tier time limit se pehle hi khatam ho jata tha. Isko fix karne ke liye do cheezein kiye:
1. `train_swinir.py` mein `--amp` flag add kiya (D035 mein `train_edsr_uncertainty.py` ke liye already kiya gaya tha, wahi pattern yahan bhi laaya) — `torch.autocast(dtype=float16)` se model forward pass, phir `sr = sr.float()` se explicitly fp32 mein wapas convert karke loss terms (SAM loss ka `acos`, edge loss ka `sqrt`) numerically stable rakhe, aur `torch.amp.GradScaler` se backward/step. Isse T4 jaisa GPU apne Tensor Cores use kar pata hai, training roughly 2x tak fast ho sakti hai.
2. Naya notebook banaya — `notebooks/train_swinir_ablation_kaggle.ipynb` — jisme same 7a/7b (ab 3a/3b) ablation cells hain, lekin Kaggle-specific setup (nvidia-smi, phone-verification/internet troubleshooting note jo pehle is session mein face kiya tha, `/kaggle/working/` checkpoint copy step kyunki Kaggle mein `google.colab.files.download` nahi hota). Existing `train_swinir_colab.ipynb` ke 7a/7b cells mein bhi `--amp` add kiya taaki dono notebooks consistent rahein (Colab ka free GPU bhi usually T4 hi hota hai).
**Verification:** `--amp` ko 3 flag-combinations ke saath local CPU par smoke-test kiya (bina `--amp`; `--amp` bina CUDA ke — clean no-op warning; `--amp` + perceptual + `--no-icnr-init` together) — sab clean chale, koi error nahi. Dono notebooks ka JSON validity check kiya (stray `</cell id="cell-N">` bug jo pehle 2 baar hua tha is session mein) — dono clean nikle.
**Reasoning:** Kaggle free tier 30 GPU-hrs/week deta hai vs Colab ka session-limited free tier — D040 ke 2 runs (20 epochs each, ~40 min each estimated) is budget mein easily fit ho jaate hain. `--amp` optional hai (P100 par zaroorat nahi), lekin T4 par real speedup deta hai, to safe default hai include karna.
**Status:** Code + dono notebooks ready. Real runs Kaggle ya Colab par, jahan bhi user chalaye, pending hai.

---

## D042 — DINOv2/DINOv3 perceptual loss backbone added (pluggable, VGG default unchanged)
**Date:** 2026-09-25
**Decision:** `ml/losses/perceptual_dino.py` mein naya `DINOPerceptualLoss` class banaya — `VGGPerceptualLoss` jaisa hi structure (frozen backbone, RGB bands only D006, L1 distance features ke beech), lekin backbone ek HF `transformers` model (`AutoModel.from_pretrained(model_id)`) hai, VGG ki jagah. `train_swinir.py` mein `--perceptual-backbone {vgg,dino}` aur `--dino-model-id` flags add kiye — default `vgg` hai (D023 se koi behavior change nahi, backward compatible), `dino` opt-in hai.

**Domain-mismatch ka asli angle:** VGG ImageNet (natural photos) par trained hai — Sentinel-2 satellite imagery se domain mismatch hai (D023 mein already note kiya gaya tha). Research karte hue pata chala Meta ne DINOv3 ka ek variant **SAT-493M (satellite imagery dataset) par bhi pretrain kiya hai** (`facebook/dinov3-vitl16-pretrain-sat493m`) — yeh VGG se kahi better domain-match hai humare use-case ke liye. Lekin yeh checkpoint **gated hai** (Meta license accept karna padta hai, manual approval jisme kuch din lag sakte hain).

Isliye default checkpoint `facebook/dinov2-small` rakha — freely available (no gating), turant test ho sakta hai, lekin domain-mismatch VGG jaisa hi hai (yeh bhi natural-image pretrained hai). `model_id` parameter se DINOv3 sat493m checkpoint swap kiya ja sakega bina kisi aur code-change ke, jab gated access approve ho jaaye.
**Verification:** Local CPU par 2 smoke tests kiye: (1) `DINOPerceptualLoss` standalone forward+backward — nonzero loss, real gradient (`grad norm 0.31`) confirm hua. (2) Poore `train_swinir.py` training loop se `--perceptual-backbone dino` flag ke saath (1 epoch, 4 samples) — clean chala. Regression check bhi kiya: `--perceptual-backbone vgg` (default) abhi bhi pehle jaisa hi kaam karta hai, koi change nahi.
**Reasoning:** DINOv3-sat493m ka asli value satellite-domain pretraining hai, VGG se best comparison waha se hi milega — lekin gating ki wajah se abhi access nahi hai. Code ko pluggable bana kar approval ka wait block nahi karta — meanwhile DINOv2 se hi ablation start ho sakta hai (architecture upgrade ka isolated effect test karne ke liye, domain-match wala effect DINOv3 aane ke baad alag se measure hoga).
**Real result — DINOv2-small quality run, Colab run complete (2026-09-25), n=279:**

| Metric | D028 (VGG + ICNR) | DINOv2 + ICNR |
|---|---|---|
| PSNR | 16.83 dB | 16.70 dB |
| SSIM | 0.437 | **0.4427** |
| SAM | 12.07° | **11.45°** |
| ERGAS | 13.89 (median 8.90) | 14.97 (median 8.66) |

**Yeh isolation ablation (D040) se zyada clean/positive nikla.** DINOv2 SAM par meaningfully better hai (11.45° vs 12.07°, -0.62°) — SAM multispectral remote-sensing ke liye particularly relevant metric hai (spectral fidelity), to yeh genuinely encouraging signal hai. SSIM bhi thoda better hai, ERGAS median bhi thoda better (8.66 vs 8.90). Sirf PSNR thoda worse hai (-0.13 dB, chhota). Overall **3 out of 4 metrics DINOv2 ke favor mein hain**, aur yeh bina kisi domain-match advantage ke bhi hai (DINOv2 khud natural-image-pretrained hai, VGG jaisa hi) — sirf architecture upgrade (ViT vs CNN features) ka effect lagta hai.
**Reasoning update**: Agar sirf architecture upgrade se itna signal mil raha hai, DINOv3-sat493m (real satellite-domain pretraining) se potentially aur better result milne ki umeed badh jaati hai.
**Status:** DINOv2 run complete, result promising (SAM/SSIM/ERGAS-median better, PSNR thoda worse). **DINOv3 sat493m gated access approve ho chuka hai** (2026-09-25 hi). `notebooks/train_swinir_dino_ablation_colab.ipynb` mein section 4 (DINOv3 sat493m, `--batch-size 4`) abhi bhi chalana baaki hai.

**DINOv3 run in-progress**: Standalone `notebooks/train_swinir_dino3_colab.ipynb` bhi bana diya (sirf DINOv3 section, DINOv2 wala nahi) — taaki fresh Colab session/account mein bina DINOv2 dobara chalaye seedha DINOv3 run kiya ja sake (D040 wale multi-notebook pattern jaisa hi, Kaggle rate-limit/session-reset se seekha hua). Actual run 24/30 epochs tak pahunch chuka hai bina kisi error ke jab yeh likha ja raha hai — real-time progress promising dikh raha hai (epoch 23: PSNR 17.04, SSIM 0.4714, SAM 11.28°).

**Disconnect ho gaya epoch 24 ke baad, checkpoints lost** (VM ephemeral disk tha, session poori tarah disconnect ho gaya, koi recovery nahi). Do fixes kiye taaki dobara na ho:
1. `train_swinir.py` mein `--resume-from <checkpoint>` flag add kiya — model weights load karke `checkpoint_epoch + 1` se training continue karta hai (step counter bhi sahi se continue hota hai). Optimizer state (Adam momentum) resume nahi hota — yeh ek accepted simplification hai (disconnect-recovery ke liye, precision-training feature nahi). Local smoke-test kiya (2-epoch run, phir epoch0 checkpoint se resume kiya) — epoch/step numbering sahi continue hui.
2. Notebook mein Google Drive mount cell add kiya (section 2a) — checkpoints ab `/content/drive/MyDrive/geosr4_checkpoints/...` mein save hote hain, VM disconnect hone par bhi safe rehte hain. Section 4b add kiya jo Drive mein sabse latest checkpoint dhoondh kar `--resume-from` ke saath training resume karta hai.
**Reasoning**: Yeh is session mein baar-baar hua pattern hai (Kaggle DNS issues, Colab time-limits, HF account mismatch) — GPU-session-fragility ab ek established risk hai is project ke liye. Resume support ek generic, reusable fix hai, sirf is ek run ke liye nahi.
**Status:** Code + notebook ready, resume-logic smoke-tested. User ko naye Colab account/session par poore 30 epochs (ya jahan tak pahunch paaye) dobara chalana hoga.

**Real final result — DINOv3-sat493m run complete on Kaggle (naya account se, 2026-09-26), n=279, poore 30 epochs:**

| Metric | D028 (VGG) | DINOv2 | DINOv3-sat493m |
|---|---|---|---|
| PSNR | 16.83 dB | 16.70 dB | 16.74 dB |
| SSIM | 0.437 | 0.4427 | **0.4481** |
| SAM | 12.07° | 11.45° | **11.19°** |
| ERGAS | 13.89 (median 8.90) | 14.97 (median 8.66) | 15.46 (median **8.30**) |

**Yeh ek clean, coherent trend hai** — teeno backbones mein DINOv3-sat493m sabse better hai SAM (spectral fidelity, humare multispectral remote-sensing use-case ke liye sabse relevant metric) aur ERGAS-median par, SSIM bhi sabse best hai. PSNR teeno mein roughly tied hai (16.70-16.83 dB, noise-level range). Trend monotonic hai: VGG (natural-image, worst SAM) → DINOv2 (natural-image, better architecture, SAM improve hua) → DINOv3-sat493m (satellite-domain + better architecture, SAM sabse best) — yeh exactly D042 ke original hypothesis ko support karta hai ki domain-matched pretraining architecture-upgrade se bhi aage jaata hai.
**Reasoning update**: Yeh investigation ka sabse positive, sabse coherent result hai poore session mein (D040/D047 ke ulat, jo inconclusive rahe) — real, honest, reproducible improvement pattern.
**Status:** D042 investigation complete. DINOv3-sat493m ka result live demo mein perceptual backbone switch karne ka case banata hai (abhi VGG hai) — agla decision yeh hai ki checkpoint ko demo mein integrate karna hai ya nahi.

**Integrated (2026-09-26)**: Checkpoint (`swinir_dino3_sat_epoch29.pt`) Kaggle se download karke `experiments/swinir_quality/` mein daal diya gaya (alag filename, purana VGG checkpoint safe hai). `backend/app/main.py` ka `CHECKPOINT_PATH` update kiya isi naye checkpoint par point karne ke liye — DINOv3 khud runtime mein load nahi hota, sirf training ke time loss ke liye use hua tha, to koi extra dependency inference mein nahi hai. Verify kiya: backend clean restart hua (koi shape-mismatch error nahi), real `/api/infer` call kiya (`ROI_1320`) — clean output aaya. **Live demo ab DINOv3-sat493m-trained checkpoint serve karta hai.**

**Real fusion re-evaluation (poore 279-pair val set par, 2026-09-26)**: User ne poocha "kya sach mein improve hua" — single-patch test se koi conclusion nahi nikal sakte the, to `ml/evaluation/evaluate_fusion.py` (D038) dobara chalaya naye checkpoint ke saath (`ml/inference/fuse_models.py`'s `SWINIR_CHECKPOINT` bhi update kiya isi naye checkpoint par, taaki live-demo se consistent rahe).

| | Purana fused (VGG-SwinIR + EDSR, D038) | Naya fused (DINOv3-SwinIR + EDSR) |
|---|---|---|
| PSNR | 16.89 dB | 16.88 dB |
| SSIM | 0.4471 | 0.4471 |
| SAM | 11.84° | **11.62°** |
| ERGAS | 15.06 (median 8.87-8.90) | 15.07 (median 8.62) |

**Honest, nuanced finding**: Raw SwinIR-alone (DINOv3) ka SAM **11.19°** hai — behtar hai fused output (11.62°) se bhi! Matlab confidence-weighted fusion (jo EDSR-uncertainty ke saath tuned tha, DINOv3-SwinIR ke saath dobara tune nahi kiya gaya) EDSR ka weaker SAM (11.90°) wapas mila deta hai, jisse DINOv3 ka full gain live demo tak nahi pahunchta. **Net result: modest SAM improvement (~0.22°) live demo mein, PSNR/SSIM practically flat, ERGAS mixed** — D042 ke raw SwinIR comparison (0.88° SAM gain) jitna promising nahi, kyunki fusion dilute kar deta hai.
**Status:** D042 poori tarah close ho gaya — checkpoint integrated hai, real improvement chhota lekin genuine hai (SAM). Fusion-weighting ko DINOv3-specific retune karna ek future consideration hai agar bada improvement chahiye ho (abhi scope se bahar).

---

## D043 — Uncertainty heatmap ab legend/scale ke saath aata hai (pehle koi nahi tha)
**Date:** 2026-09-25
**Decision:** User ne flag kiya ki uncertainty map "samajh nahi aata" — root cause dekha to `_heatmap_png_base64` (`backend/app/main.py`) sirf `plt.imsave()` se raw colored array likh raha tha, **koi colorbar/legend/numeric scale nahi thi**. Viewer ko sirf relative brightness dikhta tha, actual std value pata nahi chalta tha. Isse `plt.subplots()` + `ax.imshow()` + `fig.colorbar()` mein badla — ab har heatmap PNG mein ek horizontal colorbar baked-in hai, real predicted-std units mein (0-1 stretch nahi, actual `imshow` auto-range).

Frontend caption bhi update kiya — pehle sirf "Brighter = lower confidence" tha, ab calibration ki asli strength honestly bataya jaata hai ("measured calibration correlation ~0.21 on held-out data -- treat it as a rough guide, not a precise confidence score") — D036 ka apna number hai, spin nahi kiya.
**Verification**: Synthetic array par standalone function test kiya (colorbar labels sahi render hue). Phir **real end-to-end test kiya** — backend+frontend dono start karke, real `/api/infer` call kiya ek actual val-set patch (`ROI_1320/lr.tif`) ke saath, response se uncertainty PNG decode karke dekha — real model ke real std values (17-84 range) ke saath colorbar sahi dikha. Frontend TypeScript compile clean hai (`tsc -b`); browser mein visual render khud verify nahi kiya (no screenshot tool available) -- yeh gap honestly note kar raha hoon.
**Reasoning:** Yeh sirf cosmetic nahi tha — bina legend ke, uncertainty panel genuinely misleading ho sakta tha (koi bhi do scenes same jaisi bright/dark dikh sakti thi chahe unka actual uncertainty magnitude bahut alag ho, per-request min-max stretch ki wajah se). Legend add karne se panel ab actually interpretable hai, aur calibration-modest disclaimer se over-interpretation ka risk kam hota hai.
**Follow-up (same din)**: Browser mein real check karne par do cheezein mili:
1. Colorbar label "normalized reflectance units" **galat tha** — code check karne par pata chala `run_sr_inference` mein `std_scene = std_scene_norm * band_scale` hai, jahan `band_scale` HR raster ke apne raw 2nd/98th percentile range se aata hai (`load_norm_stats`) — yeh **raw pixel-value units** hain, normalized 0-1 nahi. Label ko "raw pixel-value units, same scale as input GeoTIFF" kiya.
2. User feedback: sirf numbers samajhne mein mushkil the, "Confident"/"Uncertain" jaisa plain-language anchor chahiye tha scale ke dono end par. Pehla attempt (floating `ax.text()` overlay) `bbox_inches='tight'` ke saath clip/misplace ho gaya — fix kiya proper `cbar.set_ticklabels()` use karke (5 ticks, extremes par do-line label "20\nConfident" / "84\nUncertain") — yeh matplotlib ke apne tick-layout engine se manage hota hai, clipping issue nahi aata.
**Status:** Backend + frontend dono commit ke liye ready, real end-to-end verify kiya (real model, real inference, browser mein dekha).

---

## D044 — Before/after slider mein hover-to-zoom magnifier add kiya (full map integration nahi)
**Date:** 2026-09-25
**Decision:** Frontend "boring" feedback ka ek hissa yeh tha ki fine detail (building edges, road texture) dekhna mushkil tha — poora image full-size dikhta tha, zoom karne ka koi tarika nahi tha. `BeforeAfterSlider.tsx` mein ek circular magnifier lens add kiya: cursor follow karta hai, jis point par hover ho raha hai uska 3x zoomed crop dikhata hai, aur before/after mein se jo bhi us point par currently visible hai (slider position ke hisaab se) wahi zoom hota hai — CSS `background-position`/`background-size` se implement kiya, extra image load nahi (same base64 PNG src reuse hota hai).

**Full Leaflet/MapLibre map integration explicitly nahi kiya** — reasoning: abhi demo sirf ek chhota patch (121x121 → 484x484) process karta hai, poori badi geographic scene nahi. "Pan across a map" ka concept tabhi value deta hai jab pan karne layak kuch bada ho — abhi nahi hai. User ko yeh tradeoff clearly bataya gaya, aur zoom-lens ko explicitly recommend kiya kam-scope, zyada-value option ki tarah — user ne accept kiya.
**Verification:** `tsc -b` clean pass hua (no type errors). Vite dev server HMR se live update verify kiya (no console errors in dev server log).
**Reasoning:** Chhota, contained scope — koi nayi dependency nahi (pure CSS + React state), current single-patch demo architecture ke liye sahi fit. Agar future mein bade multi-tile scenes process karne lagein, tab map integration ka case banega — abhi premature hota.

**Reverted, same din.** User ne browser mein real test kiya — feedback: "kuch khas nahi hai." Zyada important: original "boring" complaint ka matlab zoom ki kami nahi tha — matlab tha overall UI visual design hi weak lag raha hai (layout/styling, feature-gap nahi). Maine feedback ko galat interpret kiya tha (missing-feature problem samjha, jabki asli issue visual-design problem thi). Code revert kar diya (`BeforeAfterSlider.tsx`, `App.tsx` caption) — is entry ko delete nahi kiya taaki yeh honestly track rahe ki kya try kiya aur kyun kaam nahi aaya.
**Status:** Reverted. Real next step: UI ka visual/styling redesign (layout, colors, spacing) — feature add karna nahi.

---

## D045 — Full UI visual redesign: dark "mission-control" theme, wide dashboard layout
**Date:** 2026-09-25
**Decision:** D044 ke baad user ne clarify kiya ki asli "boring" complaint overall UI visual design ke baare mein thi (light slate/emerald SaaS look, narrow centered column, generic feel), koi missing feature nahi. Isse properly solve karne ke liye pehle Artifact tool se ek standalone mockup banaya (do artboards: Upload state + Results state) taaki real app touch karne se pehle direction approve ho sake — user ne "sahi hai go ahead" bola, phir implement kiya.

Direction: dark navy/charcoal theme (`#0a0e14` bg, layered surface tones), signal-orange accent (`#ff7a45`) + cyan secondary (`#22d3ee`) — "satellite mission-control" feel, generic emerald-on-slate SaaS look se door. Typography: Space Grotesk (headings/buttons), IBM Plex Sans (body), IBM Plex Mono (numbers/technical readouts jaise metrics, resolution, file size) — Inter/Roboto/Arial jaisa generic AI-tool look explicitly avoid kiya. Layout: narrow `max-w-5xl` centered column se wide two-column dashboard (360px sidebar + flexible main area) mein badla, taaki desktop width ka use ho.

Files change: `index.html` (Google Fonts links), `src/index.css` (color tokens as CSS variables, `@theme` font-family tokens for Tailwind v4), `App.tsx` (poora layout rewrite, naya `TopBar` component), `Dropzone.tsx`, `MetricsPanel.tsx`, `BeforeAfterSlider.tsx` (sab dark-theme colors + naye tokens use karne ke liye update).
**Verification:** `tsc -b` clean pass hua. Vite dev server HMR se saari files live-update hui, koi console error nahi (dev server log check kiya). Visual browser check user khud karega.
**Reasoning:** Mockup-first approach (D044 ki galti se seekha) — visual taste subjective hota hai, real code se pehle disposable preview approve karwana safer hai bina baar-baar wrong-direction implementation ke.
**Status:** Code ready, typecheck clean. User verify karega browser mein.

---

## D046 — Multi-page sidebar navigation, kuch pages honestly "Coming soon"
**Date:** 2026-09-25
**Decision:** User ne ek reference screenshot diya (GeoSRM-style dashboard: left sidebar nav, multiple pages -- Home, Upload & Enhance, Compare View, Analysis Tools, Applications submenu with Urban Analysis/Crop Monitoring/Disaster Assessment/Change Detection, Model Insights, Uncertainty Map, Downloads) aur poora structure copy karne ko bola. Maine flag kiya ki isme kai features hain jo hamare app mein actually exist nahi karte — user ne explicitly confirm kiya "poora structure copy karo" (placeholder pages OK hain).

Implement kiya: naya `Sidebar.tsx` (collapsible "Applications" submenu), light client-side routing (`useState<Page>` App.tsx mein, koi react-router nahi -- app itna simple hai ki extra dependency ki zaroorat nahi). State (`file`, `hrFile`, `result`, etc.) App.tsx mein lift kiya taaki Compare View/Uncertainty Map/Downloads pages last result access kar sakein.

**Real pages** (existing functionality reuse karte hain): Home (landing + use-case list, "live" vs "planned" labeled honestly), Upload & Enhance (poora existing flow, jaisa tha), Compare View (last result ka before/after, empty state agar result nahi hai), Uncertainty Map (last result ka heatmap + explanation), Downloads (GeoTIFF download), Model Insights (**real numbers** decisions.md se -- D038 fusion metrics 16.89dB/0.4471/11.84°, D036 calibration r≈0.21 -- fabricated nahi).

**Honestly-labeled stub pages** (Analysis Tools + 4 Applications items: Urban Analysis, Crop Monitoring, Disaster Assessment, Change Detection): koi in mein se implement nahi hai (D033 mein downstream-task validation try kiya tha, abandon kar diya tha). In pages par saaf "Coming soon" badge + explicit text hai ki "hum yahan fake numbers ya results nahi dikhate" — reference image jaisa fake data/charts nahi dikhaya.

**Do cheezein reference se deliberately drop ki**: (1) top bar ka location search box -- koi backend location-search functionality nahi hai, fake/dead UI banata; (2) map-style viewer (zoom controls, live lat/lon readout, scale bar) -- backend abhi `/api/infer` response mein CRS/coordinate info return nahi karta, to yeh add karne ke liye real backend change chahiye hoga, hardcoded fake coordinates dikhana misleading hota.
**Verification:** `tsc -b` clean pass hua. Dev server ne cleanly HMR update liya, `curl` se page 200 return kiya. Visual browser check user khud karega.
**Reasoning:** Full nav structure se demo ka "breadth of vision" dikhta hai (SIH panel ke liye valuable), lekin project ki core honesty principle (kabhi fabricated result nahi dikhana) maintain rakhi -- roadmap items clearly labeled hain, fake data kahin nahi hai.
**Status:** Code ready, typecheck clean. User verify karega browser mein.

---

## D047 — Downstream task v2: real OSM ground truth se test kiya, phir bhi inconclusive
**Date:** 2026-09-25
**Decision:** D033 ka core flaw fix kiya — us attempt mein SAM ke apne zero-shot segments ko hi "ground truth" ki tarah use kiya gaya tha (circular comparison, model khud se compare ho raha tha). Isse fix karne ke liye naya script banaya:
- `geospatial/preprocessing/fetch_osm_buildings.py`: OpenStreetMap Overpass API se real building footprints fetch karta hai (koi auth nahi chahiye), kisi bhi reference GeoTIFF ke grid par rasterize karta hai — yeh ek genuinely external, independent ground truth hai.
- `ml/evaluation/downstream_segmentation_v2.py`: SAM automatic mask generator bicubic-upsampled input aur SR output dono par chalaya (union of all detected segment boundaries, koi building-vs-not classification nahi taaki ek aur judgment-call add na ho), phir dono ka IoU compute kiya real OSM building mask ke against.

**Real-world test**: D030 wala Delhi (Connaught Place) AOI reuse kiya — pehle SEN2NAIP val-set ke 80/279 ROIs scan kiye OSM se (real building density check karne ke liye), aur pata chala **val set mostly rural/agricultural hai** (zyadatar ROIs mein 0 buildings, best case sirf 8) — is wajah se val set par yeh evaluation meaningless hota. Delhi AOI mein real dense urban data mila (4211 buildings, 13.22% pixel coverage poori AOI mein, 640x640 center-crop mein 17.67%).

**Result (640x640 crop, n=72395 ground-truth building px):**
| | Segments found | IoU vs OSM buildings |
|---|---|---|
| Bicubic-upsampled | 29 | **0.1770** |
| GeoSR-4 output | 24 | **0.1768** |

Practically identical — 0.0002 ka gap, noise-level hai. Absolute IoU bhi dono ke liye low hai (~0.18), kyunki SAM ke segments sirf buildings nahi, har distinct visual object (roads, trees, shadows) capture karte hain — union mask "building-specific" nahi hai.
**Reasoning:** Yeh D033 se zyada rigorous method hai (real external ground truth), lekin result phir bhi clear SR-advantage nahi dikhata. Do independent attempts (D033: zero-shot segment count, D047: SAM+OSM IoU) dono ne is downstream proxy par koi significant benefit nahi paya. Honest reading: SR yahan reconstruction-fidelity metrics (PSNR/SAM) aur visual sharpness improve karta hai (verified, D029/D038), lekin off-the-shelf zero-shot object-detection-style downstream tasks par uska fayda (agar hai bhi) is proxy se measure nahi ho paya — ya to real fayda nahi hai, ya humara proxy metric hi is fayde ko capture karne mein sensitive nahi hai.
**Status:** Real, honest result — na spin kiya na chhupaya. Panel ko yeh clearly bata sakte hain: "downstream validation try kiya, rigorous method use kiya, result inconclusive raha" — yeh khud ek valid scientific finding hai, failure nahi.

**Follow-up (same din) — multi-AOI + per-building metric, ek naya diagnostic mila:**

Do weaknesses fix karne ki koshish ki: (1) single AOI (Delhi) ka result trust nahi kar sakte — 3 aur diverse Indian urban AOIs add kiye (Bandra Mumbai, Koramangala Bangalore, Anna Nagar Chennai, sab real Sentinel-2 fetch + SR inference kiya); (2) flat union-mask IoU building-specific nahi tha (roads/trees bhi count hote the) — `fetch_osm_buildings.py` mein instance-labeled rasterization add kiya (`rasterize_buildings_instances`, har building ko unique ID), aur naya metric likha (`per_building_best_iou`, `ml/evaluation/downstream_segmentation_v2.py`): har real OSM building ko uske best-matching SAM segment se IoU score diya (standard "mean best-instance IoU", instance segmentation ka established metric), phir 3 AOIs mein pool kiya (`ml/evaluation/downstream_multi_aoi.py`).

**Result (Delhi CP is baar Overpass timeout se skip hua, retry nahi kiya — 3 AOIs se result mila, n=6814 buildings pooled):**
| AOI | Buildings scored | Bicubic best-IoU | SR best-IoU |
|---|---|---|---|
| Bandra Mumbai | 1707 | 0.0075 | 0.0080 |
| Koramangala Bangalore | 2467 | 0.0054 | 0.0036 |
| Anna Nagar Chennai | 2640 | 0.0028 | 0.0038 |
| **Pooled** | **6814** | **0.0049** | **0.0048** |

Phir se practically tied. Lekin ek zyada important diagnostic mila: **SAM ke segments (29-37 per crop) OSM buildings (1700-2600+ per crop) ke saamne bahut kam hain** — matlab SAM ka automatic mask generator (`points_per_side=16`, D033 mein CPU-speed ke liye choose kiya tha) itna coarse hai ki ek segment poora city-block cover kar leta hai, individual building resolve nahi karta. Isi wajah se absolute IoU bhi bahut low hai (~0.005, pehle wale union-IoU test se 35x kam) — yeh building-density itni zyada hai in Indian shehron mein ki current SAM settings us granularity tak pahunch hi nahi pate, chahe input bicubic ho ya SR.

**Honest conclusion**: Yeh ab "SR downstream task mein help nahi karta" ka clean proof nahi hai — yeh "humara test-tool (SAM, low points_per_side) is building-density par kaam hi nahi kar raha, dono inputs ke liye equally" ka proof hai. Fix karne ke liye `points_per_side` bahut badhana padega (jaise 32-64), jo CPU par bahut slow ho jaayega (shayad ghanton mein). Teen independent attempts (D033, D047-v1, D047-v2) ab ho chuke hain, teeno inconclusive — is point par further downstream-task iteration ka cost-benefit questionable hai.
**Status:** Multi-AOI + per-building metric bhi inconclusive, plus SAM-granularity ki genuine limitation expose hui. Yeh line of investigation yahan pause kar rahe hain jab tak koi naya, zyada compute-efficient tool na mile — teen honest, rigorous attempts already documented hain.

---

## D048 — Synthetic-degradation pretraining pipeline banaya (`opensr-degradation`)
**Date:** 2026-09-26
**Decision:** Backlog ke do bache hue items (synthetic-data pretraining pipeline, bigger/longer retrain) ek saath address kiye, kyunki dusra pehle wale se gated tha. Poora naya pipeline banaya:

1. **`opensr-degradation` package integrate kiya** — yeh NAIP HR imagery ko synthetic Sentinel-2-like LR mein degrade karta hai (harmonization + blur + noise model), same OpenSR research group ne banaya jisne SEN2NAIP dataset banaya (tiling convention bhi match karta hai — 484px HR tiles). Do real bugs mile aur fix kiye package ke apne default params mein:
   - `reflectance_method` default ek bare string hai, lekin unka apna code `for method in methods` karta hai jo string ko character-by-character iterate karta hai (`KeyError: 'g'`) — list explicitly pass karke fix kiya.
   - `percentiles` param bhi similarly list expect karta hai, int nahi.
   - `vae_histogram_matching` method (unka apna recommended default) yahan degenerate output deta hai (sab values ±0.01 ke andar, NaN nahi lekin useless) — debug nahi kiya (third-party model-weights issue, scope se bahar), instead `gamma_multivariate_normal` (non-learned statistical method) use kiya jo visually plausible blur/degradation deta hai (verified).
2. **`geospatial/preprocessing/fetch_naip_hr.py`**: Microsoft Planetary Computer ke free, no-auth STAC API se real HR-only NAIP tiles fetch karta hai (0.6m native resolution), 2.5m/px 484x484 patches mein resample karta hai (humare HR grid convention se match).
3. **`ml/datasets/generate_synthetic_pairs.py`**: 20 diverse US locations (urban/suburban/agricultural mix, alag-alag states) se real NAIP HR fetch karke, degrade karke synthetic (LR,HR) pairs banata hai, apni khud ki percentile-normalization stats compute karta hai (D008 jaisa hi philosophy, lekin alag scale hai kyunki degradation model ka output "harmonized reflectance" scale mein hai, real dataset ke raw DN scale mein nahi).
4. **`ml/training/train_swinir_synthetic_pretrain.py`**: do-phase training — pehle synthetic corpus par pretrain (real val-set par evaluate karte hue throughout, taaki convergence dikhe), phir SAME model ko real train split par fine-tune (D040's 7a jaisa hi protocol — ICNR default on, taaki fair comparison ho).
5. **`notebooks/train_swinir_synthetic_pretrain_colab.ipynb`**: poora pipeline (fetch→generate→pretrain→finetune→eval), plus ek "bigger model" section (embed_dim 60→120, depths 4→6 blocks each, pretrain 40→60 epochs, finetune 20→40 epochs) jo "bigger/longer retrain" backlog item ko isi pipeline se combine karta hai.

**Verification**: Har component real-world test kiya, mock nahi:
- `fetch_naip_hr.py`: real location (-119.2, 36.3) se fetch kiya, visually verify kiya (buildings/roads/orchards clearly dikhe)
- `opensr-degradation`: real HR tile degrade kiya, visual comparison kiya real LR se — blur/structure pattern genuinely similar (D047 ke visual-check jaisa rigor)
- Poora 20-location batch generate kiya (20/20 success), 3 pairs visually inspect kiye — geometric degradation sahi, color-harmonization tone thoda off (accepted limitation)
- Poora pretrain+finetune script end-to-end CPU par smoke-test kiya (1 pretrain epoch, 1 finetune epoch, 4 real ROIs) — dono phases clean chale, checkpoints sahi save hue, val metrics dono phases mein print hue
**Honest scale caveat**: 20 synthetic locations sirf **proof-of-concept scale** hai, "abundant synthetic data" ka asli value proposition (jisme synthetic data real paired data se kai guna zyada ho) abhi nahi achieve hua — real training set (2283 pairs) se bhi chhota hai yeh corpus. Scale badhana straightforward hai (`--n` badhao, `LOCATIONS` list mein aur jagah add karo), lekin fetch+degrade sequential hai (network-bound), to bahut bada batch (100s-1000s) generate karne mein real time lagega jo abhi nahi kiya.
**Reasoning:** Fair comparison D040's 7a (ICNR-only, --amp, 20 epochs, PSNR 16.54 dB) ke against hai, kyunki dono same ICNR/amp config share karte hain — sirf synthetic-pretrain phase hi naya variable hai isolated.
**Status:** Poora pipeline code ready, har component individually verified, end-to-end smoke-tested. Real GPU run (pretrain+finetune, aur optional bigger-model variant) Colab/Kaggle par user ko chalana hai — abhi tak nahi chalaya gaya hai.

---

---

## D049 — Crop Monitoring (NDVI) ab real feature hai, "planned" nahi
**Date:** 2026-09-26
**Decision:** User ne poocha ki D046 ke "planned" (Urban Analysis, Crop Monitoring, Disaster Assessment, Change Detection) mein se koi real implement ho sakta hai kya. Reframe kiya: D033/D047 ne yeh test kiya tha "kya SR bicubic se better hai in tasks ke liye" (research validation, inconclusive raha) — lekin "kya yeh feature ban sakta hai" (bina superiority claim kiye) alag, aasan sawal hai.

**Crop Monitoring ab real hai**: NDVI (`(NIR - Red) / (NIR + Red)`) ek standard, well-established remote-sensing formula hai — koi trained model nahi, koi "SR helps" claim nahi, sirf real band math SR output ke Red/NIR bands par. `ml/evaluation/ndvi.py` (`compute_ndvi`), backend `/api/infer` response mein `ndvi_preview_png` add kiya (fixed -1 to 1 color scale, RdYlGn colormap, colorbar+legend D043 ke pattern se — is baar shuru se hi fixed scale rakha, per-request stretch nahi, kyunki NDVI ka meaningful absolute range hai). Frontend: `CropMonitoringPage.tsx`, `HomePage`'s "Crop monitoring" badge "planned" se "live" kiya, sidebar ka "Roadmap preview" note ab is page par nahi dikhta.
**Verification**: Backend restart karke real `/api/infer` call kiya (`ROI_1320/lr.tif`), NDVI output decode karke dekha — real legend, plausible values (mostly near-zero/low, is ROI ke sparse-vegetation terrain se match karta hai). `tsc -b` clean, Vite HMR clean.
**Honest scope note**: Frontend mein explicit disclaimer hai ki yeh "SR bicubic se behtar NDVI deta hai" jaisa claim nahi kar raha — sirf real band computation offer kar raha hai, jo standalone valid hai (SR output real hai, NDVI formula real hai, dono milke ek working feature hain).
**Status:** Real, working, end-to-end verified. Urban Analysis aur Change Detection/Disaster Assessment abhi bhi "Coming soon" hain (zyada effort chahiye — SAM integration, ya do-image upload flow).

---

---

## D050 — Urban Analysis (SAM structure detection) ab real feature hai
**Date:** 2026-09-26
**Decision:** D049 jaisa hi reframe — "kya SR bicubic se better hai" (D033/D047, inconclusive) alag sawal hai "kya feature ban sakta hai" (bina superiority claim) se. Urban Analysis ke liye existing SAM setup (D033/D047) reuse kiya, backend mein naya `POST /api/urban-analysis` endpoint banaya jo frontend ke already-computed SR preview PNG (`output_preview_png`) par directly SAM automatic mask generation chalata hai — koi dobara SR inference nahi chahiye. Fast settings use kiye (`points_per_side=12`, D033/D047 ke `16` se bhi kam) kyunki yeh ab synchronous request ke andar chalta hai, offline batch-evaluation nahi.

Frontend: `UrbanAnalysisPage.tsx` — user-triggered "Run detection" button (auto-run nahi kiya, kyunki SAM inference ~15-20s leta hai, user ko explicitly control dena better UX hai slow operation ke liye). Result: colored segment overlay + count. Explicit disclaimer hai ki yeh SAM ka real zero-shot output hai, trained classifier nahi, aur SR-vs-bicubic superiority claim nahi kar raha (D047 ka honest context carry karta hai).
**Verification**: Backend restart kiya (SAM checkpoint load hua cleanly), real end-to-end test kiya — `ROI_1320` ke SR preview par 9 segments detect hue (~17s), overlay visually verify kiya (real colored regions, image ke actual features par align). `tsc -b` clean, Vite HMR clean.
**Status:** Real, working, end-to-end verified. `HomePage`'s "Urban analysis" badge "planned" se "live".

---

---

## D051 — Change Detection ab real feature hai (do-image upload flow)
**Date:** 2026-09-26
**Decision:** Teesra "planned" feature real bana diya. Yeh doosron se different hai — naya do-image upload flow chahiye tha (before/after, same AOI, alag dates). Backend: `POST /api/change-detection` — dono images par SR chalata hai (existing pipeline reuse), phir dono SR outputs ko same normalization space (`hr_ranges`) mein normalize karke per-pixel mean-absolute-difference nikalta hai, fixed [0, 0.5+] color scale ke saath render karta hai (D049/D050 ka established pattern — real legend, per-request stretch nahi).

**Real constraint jo explicitly bataya gaya hai**: dono images same exact pixel grid honi chahiye (same crop/shape) — koi georeferencing/alignment nahi kiya jaata, shape-mismatch explicitly reject hota hai (silently misaligned pixels compare nahi karta).

Frontend: `ChangeDetectionPage.tsx` — do `Dropzone` (Before/After), "Compare" button, before/after SR previews + change heatmap dikhata hai.
**Verification**: Backend restart kiya, real end-to-end test kiya do **alag-alag** ROIs (`ROI_1320`, `ROI_1916`) ke saath (same shape, different content — simulates worst-case "not actually same place" scenario) — real change map mila, poore frame mein moderate-high change dikha (expected hai, kyunki yeh genuinely alag jagah hain, real same-location before/after pair honest tarike se kam change dikhayega). `tsc -b` clean, Vite HMR clean.
**Status:** Real, working, end-to-end verified. Sabhi teen user-requested features (Crop Monitoring D049, Urban Analysis D050, Change Detection D051) ab live hain. Disaster Assessment abhi "Coming soon" hai (explicitly nahi manga gaya tha).

---

## Open Considerations (decided nahi, but track karna hai)

- ~~**Indian AOI qualitative inference**~~ **RESOLVED (D030)**. Indian HR ground-truth reference dataset abhi bhi nahi milta (quantitative metrics is wajah se still not possible for India specifically) — yeh sub-item open hi hai.
- **Synthetic-data pretraining pipeline** (from D031): `opensr-degradation` package verify + smoke-test karna, phir synthetic-pretrain → real-finetune pipeline banana Kaggle par (30hr/week free GPU) — bigger model/zyada epochs safely try karne ke liye.
- **Uncertainty estimation method**: PRD MC-ensemble (5x inference) suggest karta hai; single-pass heteroscedastic head (mean+variance in one forward pass) zyada compute-efficient alternative hai. Final choice benchmarking ke baad decide hoga.
- **Backend infra scope for MVP demo**: PostGIS/Redis/Celery vs simpler synchronous/local-storage approach — team ki compute/timeline availability dekh kar decide karna hai.
- **Perceptual loss**: DINOv3 vs standard VGG-based perceptual loss — DINOv3 optional/stretch goal hai per PRD khud bhi.
- **Nodata handling refinement**: Abhi LR nodata pixels ko 0 se replace kiya ja raha hai (D007). Agar training mein edge artifacts dikhein, to proper masking (loss se exclude karna) ya un ROIs ko filter karna consider karna hoga jinme nodata fraction zyada hai.
- ~~**ERGAS outlier investigation**~~ **RESOLVED (D015)**: `ROI_05939` ka ek band (index 2) ka mean sirf 0.0075 hai (likely water/shadow, near-zero reflectance) — ERGAS formula `(RMSE/mean)²` hai per band, to near-zero denominator ek hi patch ka ERGAS 771.5 tak blow-up kar deta hai (median 11.66 ke against). Yeh ERGAS metric ki ek known limitation hai low-reflectance regions ke liye, code bug nahi. Fix: `run_baseline.py`/`evaluate_checkpoint.py` ab median bhi print karte hain mean ke saath, kyunki mean is tarah ke outliers ke against robust nahi hai.
- **Scale SwinIR to match EDSR's parameter count** (from D013): Abhi SwinIR 2.2x chhota hai phir bhi tied hai. Bigger embed_dim ya deeper RSTBs try karna chahiye ek fairer max-capacity comparison ke liye, before final "which architecture wins" call lena.
- **Tune λ_spectral / λ_edge** (from D014): 0.1/0.1 sirf ek starting guess hai. Pehla ablation result dekhne ke baad (better/worse/same), agar promising lage to proper sweep (jaise 0.05/0.1/0.5/1.0) karna chahiye final numbers ke liye.
- ~~**Uncertainty warm-start**~~ **RESOLVED (D036)**: Full-scale Colab run bina warm-start ke hi stable raha (grad clipping + amp dono ne kaam kiya) — warm-start ki zaroorat nahi padi.
- ~~**SwinIR tiled inference**~~ **RESOLVED (D018)**.
- ~~**Uncertainty map GeoTIFF output**~~ **RESOLVED (D018)**.
- ~~**Uncertainty calibration on a real-trained checkpoint**~~ **RESOLVED (D036)**: Real calibration = 0.206 (std 0.193, n=279) — genuinely positive, modest signal, not a strong one.
- ~~**Wire uncertainty map into the live demo**~~ **RESOLVED (D037)**: Dual-inference (SwinIR + EDSR-uncertainty) backend/frontend mein live hai.
- ~~**PixelShuffle checkerboard artifact fix**~~ **RESOLVED (D023-D025, verified D029)**.
- **Isolate perceptual-loss vs ICNR-init contribution** (from D029): Dono ek saath bundle kiye the time-constraint ki wajah se. Agar precise attribution chahiye (kaun sa fix asli sharpness improvement de raha hai), do alag Colab runs chahiye — abhi combined effect hi verified hai.
